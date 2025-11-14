# nodes/generate_answer.py
import json
from openai import OpenAI
from graph.state import SelfRAGState

client = OpenAI()


def calculate_llm_score(answer: str, context: str, relevance_score: float) -> float:
    """
    LLM 신뢰도 점수 계산
    - 관련성 점수 기반
    - 답변 길이 평가 (너무 짧으면 감점)
    """
    # 기본 점수는 관련성 점수에서 시작
    base_score = relevance_score if relevance_score > 0 else 0.70

    # 답변 길이 평가 (너무 짧으면 감점)
    answer_length = len(answer)
    if answer_length < 50:
        length_penalty = 0.20
    elif answer_length < 100:
        length_penalty = 0.10
    else:
        length_penalty = 0.0

    # 최종 점수 계산
    final_score = base_score - length_penalty

    # 0.0 ~ 1.0 범위로 제한하고 소수점 2자리로 반올림
    return round(max(0.0, min(1.0, final_score)), 2)


def generate_answer_i(state: SelfRAGState) -> SelfRAGState:
    """
    통합 답변 생성 노드 (개선 버전)
    - 비의학 질문: LLM이 대화 이력을 고려하여 적절한 답변 생성
    - 의학 용어 질문: WebSearch 결과 기반 답변
    - 일반 의학 질문: RAG 문서 기반 답변
    - conversation_history를 활용하여 맥락 인식 답변 생성
    """

    # 시작 로그
    query = state.get("question", "")
    context_len = len(state.get("context", ""))
    is_terminology = state.get("is_terminology", False)
    need_quit = state.get("need_quit", False)
    print(f"• [Generate] start (context_chars={context_len}, is_terminology={is_terminology}, need_quit={need_quit})")

    # 대화 이력 가져오기
    conversation_history = state.get("conversation_history", {})
    history_summary = conversation_history.get("summary", "")
    last_conversation = conversation_history.get("last_conversation", "")
    facts = conversation_history.get("facts", [])

    # 1. 비의학 질문 처리 - LLM이 적절한 답변 생성
    if state.get("need_quit", False):
        print("• [Generate] Processing non-medical question with LLM")

        # 대화 이력 컨텍스트 생성 (직전 대화 우선)
        history_context = ""
        if last_conversation:
            history_context = f"""
직전 대화:
{last_conversation}

"""

        # 전체 대화 이력 추가 (참고용)
        if history_summary and len(history_summary) > len(last_conversation or ""):
            history_context += f"""
이전 대화 이력 (참고):
{history_summary}

"""

        # 주요 사실 추가
        if facts:
            history_context += f"""
사용자 정보:
{", ".join(facts)}

"""

        prompt = f"""{history_context}사용자 질문: {query}

위 질문에 대해 친절하고 자연스럽게 답변해주세요.

중요 작성 규칙:
- 질문에 대명사("이러한", "그것", "저것", "이", "그", "저" 등)가 있으면 **직전 대화**를 우선 참고하세요
- 직전 대화에서 답을 찾을 수 없으면 이전 대화 이력을 참고하세요
- 사용자 정보(이름, 취미 등)가 있으면 자연스럽게 반영하세요
- 자연스럽고 따뜻한 대화 톤을 유지하세요
- 간결하고 명확하게 답변하세요
        """

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        answer = res.choices[0].message.content.strip()
        state["final_answer"] = answer

        # 비의학 질문은 structured_answer를 생성하지 않음
        # 완료 로그
        answer_len = len(answer)
        print(f"• [Generate] complete (answer_chars={answer_len}, non-medical)")

        return state

    # 2. 의학 질문 처리
    query = state.get("question", "")
    context = state.get("context", "")
    sources = state.get("sources", [])
    is_terminology = state.get("is_terminology", False)

    # 컨텍스트가 없는 경우
    if not context:
        if is_terminology:
            state["final_answer"] = "죄송합니다. 관련 정보를 찾을 수 없습니다."
        else:
            state["final_answer"] = "죄송합니다. 관련 문서를 찾을 수 없습니다."
        return state

    # 3. WebSearch 결과 기반 답변 (answer_websearch 로직)
    if is_terminology:
        # 대화 이력 컨텍스트 생성 (직전 대화 우선)
        history_context = ""
        if last_conversation:
            history_context = f"""
직전 대화:
{last_conversation}

"""

        # 전체 대화 이력 추가 (참고용)
        if history_summary and len(history_summary) > len(last_conversation or ""):
            history_context += f"""
이전 대화 이력 (참고):
{history_summary}

"""

        # 주요 사실 추가
        if facts:
            history_context += f"""
사용자 정보:
{", ".join(facts)}

"""

        prompt = f"""{history_context}사용자 질문: {query}

검색된 정보:
{context}

위 정보를 바탕으로 사용자 질문에 대해 정확하고 자연스럽게 답변해주세요.
핵심 내용을 먼저 설명하고, 필요한 경우 상세 설명을 이어서 작성하세요.

중요 작성 규칙:
- 검색 결과에 있는 정보만 사용하세요
- 질문에 대명사("이러한", "그것", "저것" 등)가 있으면 **직전 대화**를 우선 참고하세요
- 직전 대화에서 맥락을 찾을 수 없으면 이전 대화 이력을 참고하세요
- 사용자 정보(이름 등)가 있으면 자연스럽게 반영하세요
- 답변 본문에 출처 번호([1], [2] 등)를 포함하지 마세요
- 의학 정보는 신중하게 전달하세요
- 긴 문서들은 간단하게 요약하여 중요 정보들만 전달해주세요
- 번호나 구조화된 형식 없이 자연스러운 문장으로 작성하세요
        """

        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}]
        )

        answer = res.choices[0].message.content.strip()

        # LLM 신뢰도 점수 계산
        llm_score = calculate_llm_score(answer, context, state.get("relevance_score", 0.0))

        # JSON 구조화된 답변 생성
        state["structured_answer"] = {
            "answer": answer,
            "references": sources,  # sources 리스트 그대로 사용
            "llm_score": llm_score,
            "relevance_score": round(state.get("relevance_score", 0.0), 2)
        }
        state["llm_score"] = llm_score

        # 답변 끝에 참고문서 목록 추가 (평문용)
        if sources:
            sources_text = "\n\n📚 참고문서:\n" + "\n".join(f"- {src}" for src in sources)
            state["final_answer"] = answer + sources_text
        else:
            state["final_answer"] = answer

    # 4. RAG 문서 기반 답변 (answer_rag 로직)
    else:
        # 대화 이력 컨텍스트 생성 (직전 대화 우선)
        history_context = ""
        if last_conversation:
            history_context = f"""
직전 대화:
{last_conversation}

"""

        # 전체 대화 이력 추가 (참고용)
        if history_summary and len(history_summary) > len(last_conversation or ""):
            history_context += f"""
이전 대화 이력 (참고):
{history_summary}

"""

        # 주요 사실 추가
        if facts:
            history_context += f"""
사용자 정보:
{", ".join(facts)}

"""

        prompt = f"""{history_context}사용자 질문: {query}

관련 문서:
{context}

위 문서를 근거로 사용자 질문에 대해 정확하고 자연스럽게 답변해주세요.
핵심 내용을 먼저 설명하고, 필요한 경우 상세 설명과 주의사항을 이어서 작성하세요.

중요 작성 규칙:
- 문서에 있는 정보만 사용하세요
- 질문에 대명사("이러한", "그것", "저것" 등)가 있으면 **직전 대화**를 우선 참고하세요
- 직전 대화에서 맥락을 찾을 수 없으면 이전 대화 이력을 참고하세요
- 사용자 정보(이름 등)가 있으면 자연스럽게 반영하세요
- 답변 본문에 문서 번호([1], [2] 등)를 포함하지 마세요
- 의학 정보는 신중하고 정확하게 전달하세요
- 추측하지 말고 문서 내용에 충실하세요
- 번호나 구조화된 형식 없이 자연스러운 문장으로 작성하세요
        """

        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}]
        )

        answer = res.choices[0].message.content.strip()

        # LLM 신뢰도 점수 계산
        llm_score = calculate_llm_score(answer, context, state.get("relevance_score", 0.0))

        # JSON 구조화된 답변 생성
        state["structured_answer"] = {
            "answer": answer,
            "references": sources,  # sources 리스트 그대로 사용
            "llm_score": llm_score,
            "relevance_score": round(state.get("relevance_score", 0.0), 2)
        }
        state["llm_score"] = llm_score

    # 완료 로그
    answer_len = len(state.get("final_answer", ""))
    print(f"• [Generate] complete (answer_chars={answer_len})")

    return state
