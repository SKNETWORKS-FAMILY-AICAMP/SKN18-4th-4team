# nodes/generate_answer.py
from openai import OpenAI

client = OpenAI()

MODEL_NAME = "gpt-5-nano"   # 모델 이름 상수
MAX_CONTEXT_LEN = 6000      # LLM 입력 제한 보호

def generate_answer(state):
    """
    evaluate_chunk 단계에서 추출된 유의미한 청크를 바탕으로
    사용자의 질문에 대한 최종 답변을 생성하는 LangGraph 노드.

    Args:
        state (dict): LangGraph 상태 (user_input, meaningful_chunks 등 포함)
    """

    query = state.get("user_input", "").strip()
    chunks = state.get("meaningful_chunks", [])

    # --- 1️⃣ 유의미한 청크 없음 ---
    if not chunks:
        state["final_answer"] = "해당 질문에 대한 충분한 정보를 찾지 못했습니다."
        state["message"] = "생성 단계 건너뜀 (유의미한 청크 없음)"
        return state

    # --- 2️⃣ context 병합 ---
    context = "\n\n".join([doc.get("page_content", "") for doc in chunks])
    context = context[:MAX_CONTEXT_LEN]

    # --- 3️⃣ 프롬프트 구성 ---
    prompt = f"""
    아래는 데이터베이스에서 검색된 문서 내용입니다.
    ---
    {context}
    ---
    사용자의 질문:
    {query}

    위 문서 내용을 근거로, 다음 기준에 따라 답변을 작성하세요.
    - 근거 기반으로만 작성
    - 명확하고 간결하게
    - 불필요한 반복, 감정 표현, 추측 금지
    - 출처 언급 시 metadata 내 source_spec 또는 creation_year 활용

    오직 최종 답변만 출력하세요.
    """

    try:
        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = res.choices[0].message.content.strip()
        state["final_answer"] = answer
        state["message"] = f"최종 답변 생성 완료 (model={MODEL_NAME})"

    except Exception as e:
        state["final_answer"] = "답변 생성 중 오류가 발생했습니다."
        state["message"] = f"답변 생성 실패: {e}"

    return state
