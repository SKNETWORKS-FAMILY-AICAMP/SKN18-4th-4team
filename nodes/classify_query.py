from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

client = OpenAI()


def classify_query(state):
    """
    사용자의 질문이 우리가 구축한 RAG 데이터로 답변 가능한지 판별하는 LangGraph 노드.
    """
    query = state.get("user_input", "").strip()

    prompt = f"""
    사용자의 질문:
    ---
    {query}
    ---
    너는 질문에 대한 전문 분석가다. 
    1. 질문이 우리가 구축한 RAG 도메인(예: 전문의료 지식, 의학 논문)과 관련 → "답변 가능"
    2. 그 외의 일반 상식/외부 주제 → "답변 불가능"

    결과로 '답변 가능' 또는 '답변 불가능' 중 하나만 출력.
    """

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}],
    )

    result = response.choices[0].message.content.strip()

    state["query_type"] = (
        "unanswerable" if "불가능" in result else "answerable"
    )
    return state
