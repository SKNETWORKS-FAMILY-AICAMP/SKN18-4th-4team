# nodes/medical_check.py
from openai import OpenAI
from graph.state import SelfRAGState

client = OpenAI()


def medical_check(state: SelfRAGState) -> SelfRAGState:
    """
    의학 용어 질문 판단 노드
    질문이 의학 용어의 정의를 묻는지 판별
    """

    query = state.get("question", "").strip()

    # 시작 로그
    print(f"• [MedicalCheck] start (question=\"{query[:50]}...\")")

    prompt = f"""
    사용자의 질문:
    ---
    {query}
    ---
    이 질문이 의학 용어나 질병명의 '정의', '뜻', '의미'를 묻는 질문입니까?

    예시:
    - "당뇨병이 뭐야?" → 용어 질문
    - "고혈압의 정의는?" → 용어 질문
    - "당뇨병 치료 방법은?" → 용어 질문 아님
    - "두통이 있을 때 어떻게 해야 해?" → 용어 질문 아님

    '용어 질문' 또는 '일반 질문' 중 하나만 출력하세요.
    """

    res = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}]
    )

    result = res.choices[0].message.content.strip()

    if "용어" in result:
        state["is_terminology"] = True
    else:
        state["is_terminology"] = False

    # 완료 로그
    print(f"• [MedicalCheck] complete (is_terminology={state['is_terminology']})")

    return state
