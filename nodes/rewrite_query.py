from openai import OpenAI

client = OpenAI()

def rewrite_query(state):
    """
    사용자의 질문을 의미적으로 동일하게 재작성하는 LangGraph 노드.
    - evaluate_chunk 단계에서 유의미한 청크가 없을 때만 호출됨.
    - 최대 1회만 재작성하도록 state['rewrite_count']로 제어.
    """

    query = state.get("user_input", "").strip()
    rewrite_count = state.get("rewrite_count", 0)

    # --- 재작성 횟수 제한 ---
    if rewrite_count >= 1:
        state["message"] = "재작성 횟수 초과. 원본 질문 그대로 유지."
        state["next_node"] = "END"
        return state

    # --- LLM 프롬프트 ---
    prompt = f"""
    사용자의 질문: {query}

    위 질문을 더 명확하고 검색에 적합하게 다시 작성하되,
    질문의 의미는 절대 바꾸지 마세요.
    불필요한 조사나 중복 표현은 줄이고,
    핵심 키워드 중심으로 간결하게 바꾸세요.

    단, 출력은 '재작성된 질문' 한 줄만 반환하세요.
    """

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        rewritten_query = res.choices[0].message.content.strip()

        # --- 상태 업데이트 ---
        state["rewrite_count"] = rewrite_count + 1
        state["rewritten_query"] = rewritten_query
        state["user_input"] = rewritten_query
        state["message"] = f"질문 재작성 완료: {rewritten_query}"
        state["next_node"] = "Retriever"  # 다시 retriever로 이동

    except Exception as e:
        state["message"] = f"질문 재작성 중 오류 발생: {e}"
        state["next_node"] = "END"

    return state
