from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .fake_compile import build
from .models import ChatConversation, Message


def _build_history(conversation: ChatConversation) -> list:
    """기존 대화 메시지를 LangChain 메시지 포맷으로 변환."""
    messages = []
    for msg in conversation.messages.order_by("created_at").only("role", "content"):
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
    return messages


def generate_ai_response(conversation: ChatConversation, prompt: str) -> tuple[str, list]:
    """
    LangChain OpenAI 모델을 호출하여 응답 텍스트와 참고문헌을 생성한다.
    """
    llm = build()
    history = _build_history(conversation)
    system_prompt = SystemMessage(
        content="당신은 의료 연구 도우미입니다. 한국어로 짧고 명확하게 답변하세요."
    )
    messages = [system_prompt, *history, HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    content = response.content if hasattr(response, "content") else str(response)
    metadata = getattr(response, "additional_kwargs", {}) or {}
    citations = metadata.get("citations", [])
    return content, citations
