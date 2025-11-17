# nodes/evaluate_chunk.py
from openai import OpenAI

client = OpenAI()

def evaluate_chunk(state):
    """
    청크 조사 노드
    검색된 문서 청크들의 관련성을 평가
    """
    query = state.get("question", "").strip()
    context = state.get("context", "")
    retrieved_count = len(state.get("retrieved_docs", []))

    # 시작 로그
    context_len = len(context)
    print(f"• [EvaluateChunk] start (총 {retrieved_count}개 chunk, context_chars={context_len}, query=\"{query[:50]}...\")")

    if not query or not context:
        state["relevance_score"] = 0.0
        state["is_relevant"] = False

        # rewrite 후에도 chunk를 찾지 못한 경우
        if state.get("rewrite_count", 0) >= 1:
            state["final_answer"] = "죄송합니다. 관련된 정보를 찾을 수 없어 답변을 제공할 수 없습니다."
            state["sources"] = []  # sources도 빈 배열로 설정
            state["structured_answer"] = {
                "type": "internal",
                "answer": "죄송합니다. 관련된 정보를 찾을 수 없어 답변을 제공할 수 없습니다.",
                "references": [],  # sources → references로 변경
                "llm_score": 0.0,
                "relevance_score": 0.0
            }
            print(f"• [EvaluateChunk] complete (검색된 chunk: 0개, 의미있는 chunk: 0개, rewrite 후 chunk 없음 - END로 이동)")
        else:
            print(f"• [EvaluateChunk] complete (검색된 chunk: 0개, 의미있는 chunk: 0개, score=0.0)")

        return state

    prompt = f"""
    질문: {query}

    검색된 컨텍스트:
    ---
    {context}
    ---

    위 컨텍스트가 질문에 답변하기에 충분히 관련성이 있는지 평가하세요.

    다음 형식으로만 답변하세요:
    관련성: [높음/낮음]
    점수: [0.0-1.0 사이의 숫자]
    이유: [간단한 설명]`
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}]
    )

    result = res.choices[0].message.content.strip()

    # 관련성 평가 결과 파싱
    if "높음" in result:
        state["is_relevant"] = True
        state["relevance_score"] = 0.80  # 기본값
    else:
        state["is_relevant"] = False
        state["relevance_score"] = 0.30  # 기본값
    # 점수 추출 시도
    if "점수:" in result:
        try:
            score_part = result.split("점수:")[1].split("\n")[0].strip()
            state["relevance_score"] = round(float(score_part), 2)  # 소수점 2자리
        except:
            pass

    state["evaluation_result"] = result

    # rewrite 후에도 관련성 있는 chunk를 찾지 못한 경우
    if not state["is_relevant"] and state.get("rewrite_count", 0) >= 1:
        state["final_answer"] = "죄송합니다. 관련된 정보를 찾을 수 없어 답변을 제공할 수 없습니다."
        state["sources"] = []  # sources도 빈 배열로 설정
        state["structured_answer"] = {
            "type": "internal",
            "answer": "죄송합니다. 관련된 정보를 찾을 수 없어 답변을 제공할 수 없습니다.",
            "references": [],  # sources → references로 변경
            "llm_score": 0.0,
            "relevance_score": 0.0
        }
        print(f"• [EvaluateChunk] complete (검색된 chunk: {retrieved_count}개, 의미있는 chunk: 0개, rewrite 후 관련성 낮음 - END로 이동)")
        return state

    # 완료 로그
    meaningful_count = retrieved_count if state['is_relevant'] else 0
    print(f"• [EvaluateChunk] complete (검색된 chunk: {retrieved_count}개, 의미있는 chunk: {meaningful_count}개, score={state['relevance_score']})")

    return state
