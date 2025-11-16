# nodes/generate_answer_i.py
import json
from openai import OpenAI
from graph.state_i import SelfRAGState

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
    통합 답변 생성 노드 (개선 버전)
    - conversation_type: "user_info" -> conversation_history 기반 답변
    - conversation_type: "non_medical" -> 안내 메시지
    - conversation_type: "medical" -> RAG 문서 기반 답변
    """

    # 시작 로그
    query = state.get("question", "")
    conversation_type = state.get("conversation_type", "medical")
    context_len = len(state.get("context", ""))
    is_terminology = state.get("is_terminology", False)
    print(f"• [Generate] start (type={conversation_type}, context_chars={context_len}, is_terminology={is_terminology})")

    # 1. 사용자 정보 질문 처리 (user_info)
    if conversation_type == "user_info":
        # conversation_history에서 사용자 정보 추출
        conversation_history = state.get("conversation_history", [])

        # List[Dict[str, str]] 형식의 대화 이력을 컨텍스트로 변환
        history_context = ""
        if conversation_history:
            history_lines = []
            # 사용자 정보는 비교적 긴 히스토리가 필요하므로, 최근 5턴(=10개 메시지)까지 사용
            for msg in conversation_history[:10]:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    history_lines.append(f"사용자: {content}")
                elif role == "assistant":
                    history_lines.append(f"어시스턴트: {content}")
            history_context = "\n".join(history_lines)

        prompt = f"""
사용자 질문: {query}

이전 대화 이력:
{history_context if history_context else "(이전 대화 없음)"}

위 대화 이력을 바탕으로 사용자 질문에 간단하고 자연스럽게 답변하세요.
중요 규칙:
- 이전 대화 이력에서 사용자가 말한 정보(이름, 나이, 특징 등)를 찾아서 답변하세요
- 대화 이력 전체를 꼼꼼히 확인하세요 (최근 대화뿐만 아니라 오래된 대화도 확인)
- 정보를 찾았으면 자연스럽게 답변하세요
- 사용자가 이름에 대해서만 정보를 제공했거나 이름을 물어보았다면, '**님 안녕하세요!' 라고만 답변하세요
- 정말로 정보가 없는 경우에만 "죄송합니다. 해당 정보를 찾을 수 없습니다."라고 답변하세요
        """

        # 디버깅: 프롬프트 출력
        print(f"• [Generate] user_info prompt (history_len={len(conversation_history)})")

        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = res.choices[0].message.content.strip()

        state["final_answer"] = answer
        state["structured_answer"] = {
            "answer": answer,
            "sources": [],
            "confidence": 1.0
        }
        state["llm_score"] = 1.0
        print(f"• [Generate] Answered from conversation history")
        return state

    # 2. 의학 질문 처리 (medical)
    context = state.get("context", "")
    sources = state.get("sources", [])
    conversation_history = state.get("conversation_history", [])
    is_follow_up = state.get("is_follow_up", False)

    # conversation_history를 컨텍스트로 변환 (follow-up일 때만 사용)
    history_context = ""
    if is_follow_up and conversation_history:
        history_lines = []
        # medical 질문의 follow-up은 직전 1턴(=2개 메시지)만 사용
        for msg in conversation_history[:2]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                history_lines.append(f"사용자: {content}")
            elif role == "assistant":
                history_lines.append(f"어시스턴트: {content}")
        history_context = "\n".join(history_lines)

    # 컨텍스트가 없는 경우 처리
    if not context:
        if is_terminology:
            state["final_answer"] = "죄송합니다. 관련 정보를 찾을 수 없습니다."
        else:
            state["final_answer"] = "죄송합니다. 관련 문서를 찾을 수 없습니다."
        return state

    # 4. WebSearch 결과 기반 답변 (answer_websearch 로직)
    if is_terminology:
        history_block = (
            f"\n이전 대화 이력:\n{history_context}\n"
            if history_context
            else ""
        )

        prompt = f"""
사용자 질문: {query}

검색된 정보:
{context}

{history_block}

사용자가 이 전에 말한 내용을 기반으로 후속질문을 하는 경우에만 이전 대화를 참고하세요.
이전 대화 이력의 내용이 사용자의 질문과 관련이 없다면 이전 대화 이력을 참고하지 마세요.
위 정보를 바탕으로 사용자 <질문>에 대해 정확하고 자연스럽게 답변해주세요.
질문에 맞는 핵심답변을 먼저 작성하세요. 
필요한 경우 상세 설명을 이어서 작성하세요.

중요 작성 규칙:
- 검색 결과에 있는 정보만 사용하세요
- **반드시 답변 내용 뒤에 출처 번호를 [1], [2] 형식으로 표시하세요**
- 예시: "당뇨병은 혈당 조절에 문제가 생기는 질환입니다[1]."
- 이전 대화 이력이 있으면 자연스럽게 활용하세요
- 의학 정보는 신중하게 전달하세요
- 긴 문서들은 중요 정보들만 전달해주세요
- ** 절대로 답변 마지막에 참고 출처를 사용하지 마세요.
- 핵심 단어에 ** markdown 강조 표현을 적용하세요
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
            "references": sources,
            "llm_score": llm_score,
            "relevance_score": round(state.get("relevance_score", 0.0), 2)
        }
        state["llm_score"] = llm_score

    # 5. RAG 문서 기반 답변 (answer_rag 로직)
    else:
        history_block = (
            f"\n이전 대화 이력:\n{history_context}\n"
            if history_context
            else ""
        )

        prompt = f"""
사용자 질문: {query}

관련 문서:
{context}

{history_block}

위 문서를 근거로 사용자 질문에 대해 정확하고 자연스럽게 답변해주세요.

답변 구조:
질문에 맞는 핵심답변을 먼저 작성하세요. 
필요한 경우 상세 설명을 이어서 작성하세요.

중요 작성 규칙:
- 문서에 있는 정보만 사용하세요
- 답변 본문에 문서 번호([1], [2] 등)를 포함하지 마세요
- 이전 대화 이력이 있으면 자연스럽게 활용하세요
- 의학 정보는 신중하고 정확하게 전달하세요
- 추측하지 말고 문서 내용에 충실하세요
- 번호나 구조화된 형식 없이 자연스러운 문장으로 작성하세요
- 핵심 단어에 ** markdown 강조 표현을 적용하세요
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
            "references": sources,
            "llm_score": llm_score,
            "relevance_score": round(state.get("relevance_score", 0.0), 2)
        }
        state["llm_score"] = llm_score

    # 완료 로그
    answer_len = len(state.get("final_answer", ""))
    print(f"• [Generate] complete (answer_chars={answer_len})")

    return state
