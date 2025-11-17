# nodes/classifier_i.py
from openai import OpenAI
from graph.state import SelfRAGState

client = OpenAI()


def classifier(state: SelfRAGState) -> SelfRAGState:
    """
    Classifier 노드 (개선 버전 - 맥락 인식)
    사용자 질문의 유형을 conversation_type으로 분류
    - "medical": 의학 관련 질문
    - "user_info": 사용자 정보 (이름 등) 관련
    - "non_medical": 의학 무관 질문

    conversation_history를 활용하여 대명사 참조 질문 처리
    """

    query = state.get("question", "").strip()

    # 원본 질문 저장 (처음 입력받은 질문)
    if "original_question" not in state:
        state["original_question"] = query

    # conversation_history 가져오기 (최근 2턴 = 4개 메시지만 사용)
    conversation_history = state.get("conversation_history", [])
    recent_history = conversation_history[:4] if conversation_history else []

    # 시작 로그
    print(f"• [Classifier] start (question=\"{query[:50]}...\", history_len={len(recent_history)})")

    if not query:
        state["conversation_type"] = "non_medical"
        state["final_answer"] = """죄송합니다. 저는 의학 질문에만 답할 수 있습니다.

의학, 건강, 질병, 증상, 치료 등과 관련된 질문을 해주시면 도움을 드리겠습니다.

예시:
- "당뇨병이란 무엇인가요?"
- "고혈압의 증상은 무엇인가요?"
- "독감 예방접종은 언제 받는 것이 좋나요?"
        """.strip()
        print(f"• [Classifier] complete (conversation_type=non_medical)")
        return state

    # conversation_history를 텍스트로 변환
    history_context = ""
    if recent_history:
        history_lines = []
        for msg in recent_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                history_lines.append(f"사용자: {content}")
            elif role == "assistant":
                history_lines.append(f"어시스턴트: {content}")
        history_context = "\n".join(history_lines)

    prompt = f"""
    사용자의 질문:
    ---
    {query}
    ---

    이전 대화 이력 (최근 2턴):
    ---
    {history_context if history_context else "(이전 대화 없음)"}
    ---

    위 맥락을 고려하여 이 질문이 어떤 유형에 속하는지 분류하세요.

    1단계: 질문 유형(type) 분류
    - "의학 관련": 의학, 건강, 질병, 증상, 치료 등과 관련된 **새로운 정보 요청**
      예: "당뇨병이란?", "고혈압 증상은?", "독감 치료법은?"
      **중요**: 질문에 "그 모델", "그거", "그 치료법" 같은 대명사가 있고, 이전 대화가 의학 관련이었다면 → 의학 관련
      예: 이전 대화에서 "Cox 모델"을 언급했고, 현재 질문이 "그 모델에서 샘플 120명이면 적절할까?" → 의학 관련

    - "사용자 정보": 다음 두 경우를 포함
      1) 사용자의 이름 정보를 알려주었거나 이름을 다시 물어보는 경우
         예: "내 이름은 홍길동이야", "내 이름이 뭐야?", "내 이름 알려줘"
      2) **직전 대화 내용 자체를 확인하는 질문** (히스토리 회상)
         예: "방금 뭐라고 했어?", "아까 말한 거 다시 알려줘", "직전에 물어본 내용 알려줘",
             "내가 방금 질문한 게 뭐였어?", "지금까지 무슨 얘기했어?"
         → 이런 질문들은 이전 대화 **내용 자체**를 다시 확인하려는 것
      **주의**: "그 모델에서..."처럼 이전 내용을 **바탕으로 새로운 질문**을 하는 것은 "의학 관련"입니다.

    - "의학 무관": 의학, 건강, 질병, 증상, 치료 등과 관련되지 않은 질문이면서
      사용자 정보나 대화 이력 확인도 아닌 경우
      예: "날씨 어때?", "오늘 뉴스 알려줘", "파이썬 코드 짜줘"

    2단계: 후속 질문 여부(follow_up) 판정
    - follow_up = true:
      직전 의학 질문/답변의 내용을 이어서 묻는 경우
      예: 직전에 EGFR 관련 연구를 이야기했고, 이번 질문이 "그 연구에서 PFS는 어땠어?"
    - follow_up = false:
      이전 대화와 주제가 다르거나, 이전 대화의 질문 및 답변과 전혀 다른 내용이거나, 독립적인 새로운 질문인 경우

    아래 JSON 형식으로만 출력하세요. 다른 텍스트는 절대 출력하지 마세요.

    {{
      "type": "의학 관련" 또는 "사용자 정보" 또는 "의학 무관" 중 하나,
      "follow_up": true 또는 false
    }}
    """

    res = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_result = res.choices[0].message.content.strip()

    # 기본값
    conv_type = "medical"
    is_follow_up = False

    # JSON 파싱 시도
    try:
        import json

        parsed = json.loads(raw_result)
        conv_type_raw = parsed.get("type", "").strip()
        is_follow_up = bool(parsed.get("follow_up", False))
    except Exception:
        # 실패 시 기존 문자열 기반 분류에 fallback
        conv_type_raw = raw_result
        is_follow_up = False

    if "의학 무관" in conv_type_raw:
        conv_type = "non_medical"
        state["final_answer"] = """죄송합니다. 저는 의학 질문에만 답할 수 있습니다.

의학, 건강, 질병, 증상, 치료 등과 관련된 질문을 해주시면 도움을 드리겠습니다.

예시:
- "당뇨병이란 무엇인가요?"
- "고혈압의 증상은 무엇인가요?"
- "독감 예방접종은 언제 받는 것이 좋나요?"
        """.strip()
    elif "사용자 정보" in conv_type_raw:
        conv_type = "user_info"
    else:
        conv_type = "medical"

    state["conversation_type"] = conv_type
    state["is_follow_up"] = is_follow_up

    # 완료 로그
    print(f"• [Classifier] complete (conversation_type={state['conversation_type']}, is_follow_up={state.get('is_follow_up')})")

    return state
