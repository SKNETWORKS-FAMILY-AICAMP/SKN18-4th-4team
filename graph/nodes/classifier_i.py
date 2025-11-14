# nodes/classifier_i.py
from openai import OpenAI
from graph.state import SelfRAGState

client = OpenAI()


def classifier(state: SelfRAGState) -> SelfRAGState:
    """
    Classifier 노드
    사용자 질문을 3가지로 분류:
    1. 의학 관련 질문
    2. 사용자 신상정보 (이름, 나이, 거주지, 직업 등)
    3. 일반 잡담 (거부 대상)

    원본 질문을 original_question에 저장
    """

    query = state.get("question", "").strip()

    # 원본 질문 저장 (처음 입력받은 질문)
    if "original_question" not in state:
        state["original_question"] = query

    # 시작 로그
    print(f"• [Classifier] start (question=\"{query[:50]}...\")")

    if not query:
        state["question_type"] = "general_chat"
        print(f"• [Classifier] complete (question_type=general_chat)")
        return state

    prompt = f"""
사용자의 질문:
---
{query}
---

이 질문을 다음 3가지 중 하나로 분류하세요:

1. **의학 관련**: 의학, 건강, 질병, 증상, 치료, 약물, 진단 등과 관련된 질문
2. **신상정보**: 사용자가 자신의 이름, 나이, 거주지, 직업, 성별, 취미, 가족관계 등 개인정보를 알려주는 경우
3. **일반 잡담**: 위 두 가지에 해당하지 않는 일반적인 대화나 질문

다음 중 정확히 하나만 출력하세요:
- 의학 관련
- 신상정보
- 일반 잡담
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    result = res.choices[0].message.content.strip()

    # 분류 결과에 따라 question_type 설정
    if "의학 관련" in result:
        state["question_type"] = "medical"
        state["need_quit"] = False
    elif "신상정보" in result:
        state["question_type"] = "personal_info"
        state["need_quit"] = False  # 신상정보는 저장해야 하므로 quit 아님
    else:
        state["question_type"] = "general_chat"
        state["need_quit"] = True  # 일반 잡담은 거부

    # 완료 로그
    print(f"• [Classifier] complete (question_type={state['question_type']})")

    return state
