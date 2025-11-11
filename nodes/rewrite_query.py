# nodes/rewrite_query.py
from openai import OpenAI

client = OpenAI()

MAX_REWRITE_ATTEMPTS = 1  # ✅ 여기서 한도 조정 가능

def rewrite_query(state):
    """
    사용자의 질문을 의미적으로 동일하게 재작성하는 LangGraph 노드.
    - evaluate_chunk 단계에서 유의미한 청크가 없을 때 호출됨.
    - 재작성 시도는 MAX_REWRITE_ATTEMPTS로 제한.
    """

    query = state.get("user_input", "").strip()
    rewrite_count = state.get("rewrite_count", 0)

    # --- 재작성 횟수 제한 ---
    if rewrite_count >= MAX_REWRITE_ATTEMPTS:
        state["message"] = f"재작성 {MAX_REWRITE_ATTEMPTS}회 초과. 원본 질문 유지."
        state["next_node"] = "END"
        return state

    prompt = f"""
    사용자의 질문: {query}

    위 질문을 더 명확하고 검색에 적합하게 다시 작성하되,
    의미는 변경하지 마세요.
    불필요한 조사나 중복 표현은 제거하고,
    핵심 키워드 중심으로 간결하게 표현하세요.

    출력은 '재작성된 질문' 한 줄만 반환하세요.
    """

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        rewritten_query = res.choices[0].message.content.strip()

        state["rewrite_count"] = rewrite_count + 1
        state["rewritten_query"] = rewritten_query
        state["user_input"] = rewritten_query
        state["message"] = f"질문 재작성 완료 ({state['rewrite_count']}회차): {rewritten_query}"
        state["next_node"] = "Retriever"

    except Exception as e:
        state["message"] = f"질문 재작성 중 오류 발생: {e}"
        state["next_node"] = "END"

    return state
