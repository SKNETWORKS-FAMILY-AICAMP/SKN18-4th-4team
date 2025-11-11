from openai import OpenAI
import re


client = OpenAI()

def evaluate_chunk(state, vectorstore=None, threshold: float = 0.4):
    """
    retriever 단계에서 가져온 청크들 중에서
    실제로 질문에 의미 있게 답변할 수 있는 청크만 필터링하는 노드.

    Args:
        state (dict): LangGraph 상태 (user_input, retrieved_docs 등 포함)
        vectorstore: 미사용 (향후 확장용)
        threshold (float): 관련성 점수 임계값 (기본 0.4)
    """

    query = state.get("user_input", "").strip()
    retrieved_docs = state.get("retrieved_docs", [])

    # --- 검색 결과 없음 ---
    if not retrieved_docs:
        state["is_relevant"] = False
        state["meaningful_chunks"] = []
        state["message"] = "검색된 문서가 없습니다."
        return state

    meaningful_chunks = []

    # --- 각 청크별 관련도 평가 ---
    for doc in retrieved_docs:
        content = doc.get("page_content", "").strip()

        prompt = f"""
        질문: {query}
        문서 내용: {content[:700]}

        위 문서가 질문에 직접적으로 도움이 되는가?
        관련성 점수를 0.0~1.0 사이 실수 하나로만 출력해.
        """

        try:
            res = client.chat.completions.create(
                model="gpt-5-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            text = res.choices[0].message.content.strip()
            match = re.search(r"([0-1](?:\.\d+)?)", text)
            score = float(match.group(1)) if match else 0.0

            # --- threshold 이상이면 유의미한 청크로 판정 ---
            if score >= threshold:
                meaningful_chunks.append(doc)

        except Exception as e:
            # API 호출 실패 시 해당 청크 스킵
            continue

    # --- 상태 업데이트 ---
    state["meaningful_chunks"] = meaningful_chunks
    state["is_relevant"] = len(meaningful_chunks) > 0
    state["message"] = f"유의미한 청크 {len(meaningful_chunks)}개 검출"

    return state
