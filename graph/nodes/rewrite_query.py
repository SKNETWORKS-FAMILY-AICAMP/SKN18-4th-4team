# nodes/rewrite_query.py
from openai import OpenAI

client = OpenAI()

def rewrite_query(state):
    """
    질문 재작성 노드
    원래 질문을 더 명확하고 검색하기 쉽게 재작성
    """
    original_query = state.get("question", "").strip()

    if not original_query:
        state["rewritten_question"] = ""
        return state

    # 평가 결과가 있다면 참고
    evaluation_result = state.get("evaluation_result", "")

    prompt = f"""
    원래 질문: {original_query}

    {f"이전 검색 평가 결과: {evaluation_result}" if evaluation_result else ""}

    위 질문을 더 명확하고 정보 검색에 적합하도록 재작성해주세요.
    재작성 시 다음을 고려하세요:
    1. 핵심 키워드를 명확히
    2. 모호한 표현을 구체화
    3. 검색 엔진이 이해하기 쉬운 형태로

    재작성된 질문만 출력하세요.
    """

    res = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}]
    )

    rewritten = res.choices[0].message.content.strip()

    # 재작성된 질문을 question 필드에 업데이트
    state["rewritten_question"] = rewritten
    state["question"] = rewritten  # 다음 검색에 사용될 수 있도록

    # 재작성 횟수 증가
    state["rewrite_count"] = state.get("rewrite_count", 0) + 1

    return state
