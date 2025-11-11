from openai import OpenAI

client = OpenAI()

def generate_answer(state):
    """
    evaluate_chunk 단계에서 추출된 유의미한 청크들을 바탕으로
    사용자의 질문에 대한 최종 답변을 생성하는 LangGraph 노드.

    Args:
        state (dict): LangGraph 상태 (user_input, meaningful_chunks 등 포함)
    """

    query = state.get("user_input", "").strip()
    chunks = state.get("meaningful_chunks", [])

    # --- 1️⃣ 유의미한 청크가 없을 경우 ---
    if not chunks:
        state["final_answer"] = "해당 질문에 대한 충분한 정보를 찾지 못했습니다."
        state["message"] = "생성 단계 건너뜀 (유의미한 청크 없음)"
        return state

    # --- 2️⃣ 청크들을 하나의 context로 병합 ---
    context = "\n\n".join([doc.get("page_content", "") for doc in chunks])
    context = context[:6000]  # 모델 입력 제한 보호

    # --- 3️⃣ LLM 프롬프트 구성 ---
    prompt = f"""
    아래는 의학 데이터베이스에서 검색된 문서 내용입니다.
    ---
    {context}
    ---

    사용자의 질문:
    {query}

    위 문서 내용을 근거로,
    질문에 대한 명확하고 근거 기반의 답변을 작성하세요.
    다음 기준을 지키세요:
    - 의학 전문가의 설명처럼 신뢰성 있게
    - 정확하고 간결하게
    - 불필요한 반복, 추측, 감정 표현 금지
    - 출처를 포함할 경우 metadata 내 source_spec 또는 creation_year를 활용

    최종 답변만 출력하세요.
    """

    try:
        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        answer = res.choices[0].message.content.strip()
        state["final_answer"] = answer
        state["message"] = "최종 답변 생성 완료"

    except Exception as e:
        state["final_answer"] = f"답변 생성 중 오류 발생: {e}"
        state["message"] = "답변 생성 실패"

    return state