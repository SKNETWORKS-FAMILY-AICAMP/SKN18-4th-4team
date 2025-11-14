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


def generate_answer(state: SelfRAGState) -> SelfRAGState:
    """
    통합 답변 생성 노드
    - 비의학 질문: 안내 메시지
    - 의학 용어 질문: WebSearch 결과 기반 답변
    - 일반 의학 질문: RAG 문서 기반 답변
    """

    # 시작 로그
    query = state.get("question", "")
    context_len = len(state.get("context", ""))
    is_terminology = state.get("is_terminology", False)
    print(f"• [Generate] start (context_chars={context_len}, is_terminology={is_terminology})")

    # 1. 비의학 질문 처리 (guidance 로직)
    if state.get("need_quit", False):
        state["final_answer"] = """
죄송합니다. 현재 시스템은 의학 관련 질문만 답변할 수 있습니다.

의학, 건강, 질병, 증상, 치료 등과 관련된 질문을 해주시면 도움을 드리겠습니다.

예시:
- "당뇨병이란 무엇인가요?"
- "고혈압의 증상은 무엇인가요?"
- "독감 예방접종은 언제 받는 것이 좋나요?"
        """.strip()
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
        prompt = f"""
사용자 질문: {query}

검색된 정보:
{context}

위 정보를 바탕으로 사용자 질문에 대해 정확하고 자연스럽게 답변해주세요.
핵심 내용을 먼저 설명하고, 필요한 경우 상세 설명을 이어서 작성하세요.

중요 작성 규칙:
- 검색 결과에 있는 정보만 사용하세요
- 의학 정보는 신중하게 전달하세요
- 긴 문서들은 간단하게 요약하여 중요 정보들만 전달해주세요
- 번호나 구조화된 형식 없이 자연스러운 문장으로 작성하세요
- 핵심 단어에 ** markdown 강조 표현을 적용하세요.
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
        prompt = f"""
사용자 질문: {query}

관련 문서:
{context}

위 문서를 근거로 사용자 질문에 대해 정확하고 자연스럽게 답변해주세요.
핵심 내용을 먼저 설명하고, 필요한 경우 상세 설명과 주의사항을 이어서 작성하세요.

중요 작성 규칙:
- 문서에 있는 정보만 사용하세요
- 답변 본문에 문서 번호([1], [2] 등)를 포함하지 마세요
- 의학 정보는 신중하고 정확하게 전달하세요
- 추측하지 말고 문서 내용에 충실하세요
- 번호나 구조화된 형식 없이 자연스러운 문장으로 작성하세요
- 핵심 단어에 ** markdown 강조 표현을 적용하세요.
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
