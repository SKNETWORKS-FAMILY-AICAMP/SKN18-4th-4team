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

    if not query or not context:
        state["relevance_score"] = 0.0
        state["is_relevant"] = False
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
        messages=[{"role": "user", "content": prompt}]
    )

    result = res.choices[0].message.content.strip()

    # 관련성 평가 결과 파싱
    if "높음" in result:
        state["is_relevant"] = True
        state["relevance_score"] = 0.8  # 기본값
    else:
        state["is_relevant"] = False
        state["relevance_score"] = 0.3  # 기본값
    # 점수 추출 시도
    if "점수:" in result:
        try:
            score_part = result.split("점수:")[1].split("\n")[0].strip()
            state["relevance_score"] = float(score_part)
        except:
            pass

    state["evaluation_result"] = result

    return state
