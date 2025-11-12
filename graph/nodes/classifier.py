# nodes/classifier.py
from openai import OpenAI
from graph.state import SelfRAGState

client = OpenAI()


def classifier(state: SelfRAGState) -> SelfRAGState:
    """
    Classifier 노드
    사용자 질문이 의학 관련 여부를 판별
    """
    query = state.get("question", "").strip()

    if not query:
        state["need_quit"] = True
        return state

    prompt = f"""
    사용자의 질문:
    ---
    {query}
    ---
    이 질문이 의학, 건강, 질병, 증상, 치료 등과 관련된 질문입니까?

    '의학 관련' 또는 '의학 무관' 중 하나만 출력하세요.
    """

    res = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}]
    )

    result = res.choices[0].message.content.strip()

    if "의학 무관" in result:
        state["need_quit"] = True
    else:
        state["need_quit"] = False

    return state
