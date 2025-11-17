# nodes/rewrite_query.py
from openai import OpenAI

client = OpenAI()

def rewrite_query(state):
    """
    질문 재작성 노드
    원래 질문을 더 명확하고 검색하기 쉽게 재작성
    """
    original_query = state.get("question", "").strip()
    conversation_type = state.get("conversation_type", "medical")
    is_follow_up = state.get("is_follow_up", False)
    conversation_history = state.get("conversation_history", [])

    # 시작 로그
    print(f"• [QueryRewrite] start (question=\"{original_query[:50]}...\")")

    if not original_query:
        state["rewritten_question"] = ""
        print(f"• [QueryRewrite] complete (rewritten=\"\")")
        return state

    # 평가 결과가 있다면 참고
    evaluation_result = state.get("evaluation_result", "")

    # follow-up 의료 질문인 경우에만 직전 1턴 히스토리를 포함
    history_context = ""
    if conversation_type == "medical" and is_follow_up and conversation_history:
        history_lines = []
        for msg in conversation_history[:2]:  # 직전 1턴 = 2개 메시지
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                history_lines.append(f"사용자: {content}")
            elif role == "assistant":
                history_lines.append(f"어시스턴트: {content}")
        history_context = "\n".join(history_lines)

    history_block = (
        f"\n이전 대화 이력 (직전 1턴):\n{history_context}\n"
        if history_context
        else ""
    )

    prompt = f"""
원래 질문: {original_query}
{history_block}
{f"이전 검색 평가 결과: {evaluation_result}" if evaluation_result else ""}

위 정보를 바탕으로, 사용자 질문의 핵심 의도를 유지하면서 검색 최적화 쿼리로 재작성하세요.

중요 규칙:
- 질병명, 장기, 암종, 표적/약물, 치료 단계 등 의학 용어는 명확하게 포함하고 약어는 가능하면 풀어서 작성하세요.
- follow-up 질문인 경우에도, 직전 대화의 주제(질환/장기/치료법 등)를 그대로 유지하세요.
- 특정 주제 관련 쿼리를 만들 때, 다른 주제의 키워드를 임의로 추가하거나 섞지 마세요.
- 재작성된 쿼리가 가장 전문적이고 구체적인 임상 문헌을 검색하도록 만드세요.

재작성된 질문만 출력하세요.
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}]
    )

    rewritten = res.choices[0].message.content.strip()

    # 재작성된 질문을 question 필드에 업데이트
    state["rewritten_question"] = rewritten
    state["question"] = rewritten  # 다음 검색에 사용될 수 있도록

    # 재작성 횟수 증가
    state["rewrite_count"] = state.get("rewrite_count", 0) + 1

    # 완료 로그
    print(f"• [QueryRewrite] complete (rewritten=\"{rewritten[:50]}...\", count={state['rewrite_count']})")

    return state
