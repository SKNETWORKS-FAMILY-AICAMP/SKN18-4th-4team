# nodes/personal_info_i.py
from openai import OpenAI
from graph.state import SelfRAGState
import json

client = OpenAI()


def personal_info_handler(state: SelfRAGState) -> SelfRAGState:
    """
    신상정보 처리 노드
    사용자가 제공한 신상정보(이름, 나이, 거주지, 직업 등)를 추출하여
    structured_answer에 저장하고 간단한 응답 생성
    """
    print("• [Personal Info] start")

    query = state.get("question", "")

    # 대화 이력에서 추가 컨텍스트 가져오기
    conversation_history = state.get("conversation_history", {})
    last_conversation = conversation_history.get("last_conversation", "")

    # 신상정보 추출 프롬프트
    extract_prompt = f"""
사용자가 자신의 신상정보를 알려주고 있습니다.

{f"직전 대화: {last_conversation}" if last_conversation else ""}

현재 질문: {query}

다음 정보를 추출하세요:
- 이름
- 나이
- 거주지 (사는 곳)
- 직업
- 성별
- 취미
- 가족관계
- 기타 개인정보

추출한 정보를 다음 JSON 형식으로 출력하세요:
{{
  "facts": ["이름: 홍길동", "나이: 30세", "거주지: 서울", ...]
}}

정보가 없으면 빈 배열을 반환하세요.
"""

    extract_res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": extract_prompt}],
        response_format={"type": "json_object"}
    )

    extracted_json = extract_res.choices[0].message.content.strip()

    try:
        extracted_data = json.loads(extracted_json)
        facts = extracted_data.get("facts", [])
    except:
        facts = []

    print(f"• [Personal Info] Extracted {len(facts)} facts: {facts}")

    # 응답 생성 프롬프트
    answer_prompt = f"""
사용자가 자신의 정보를 알려주었습니다:
{query}

추출된 정보: {", ".join(facts) if facts else "없음"}

자연스럽고 따뜻하게 응답해주세요.
예시:
- "네, 기억하겠습니다!"
- "알겠습니다. 앞으로 그 점을 기억하겠습니다."
- "네, 잘 알겠습니다!"

짧고 간단하게 1-2문장으로 답변하세요.
"""

    answer_res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": answer_prompt}]
    )

    answer = answer_res.choices[0].message.content.strip()

    # structured_answer에 저장 (메모리 저장용)
    state["structured_answer"] = {
        "answer": answer,
        "facts": facts,
        "is_personal_info": True
    }

    # final_answer에도 저장 (사용자에게 보여줄 응답)
    state["final_answer"] = answer

    print(f"• [Personal Info] complete (answer=\"{answer}\")")

    return state
