from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

try:
    from django.conf import settings
except ImportError:  # pragma: no cover - django 미설치 환경
    settings = None

from .fake_compile import build as fake_build
from .llm import get_llm
from .models import ChatConversation, Message

# Django 앱(django_app)보다 한 단계 위에 있는 프로젝트 루트를 파이썬 경로에 추가
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

try:
    from graph.compile import create_medical_rag_workflow
except ImportError as exc:  # pragma: no cover - 환경에 따라 graph 패키지가 없을 수 있음
    create_medical_rag_workflow = None
    _GRAPH_IMPORT_ERROR = exc
else:
    _GRAPH_IMPORT_ERROR = None

_graph_app: Any | None = None


def _use_fake_backend() -> bool:
    """
    설정값에 따라 임시 fake compile 백엔드를 사용할지 여부.
    """
    if settings is None:
        return False
    return getattr(settings, "CHAT_USE_FAKE_COMPILE", False)


def _get_graph_app():
    """
    LangGraph 워크플로우를 지연 로딩하여 재사용
    """
    global _graph_app
    if create_medical_rag_workflow is None:
        raise RuntimeError("LangGraph 모듈을 불러올 수 없습니다.") from _GRAPH_IMPORT_ERROR
    if _graph_app is None:
        _graph_app = create_medical_rag_workflow()
    return _graph_app


def _format_citations(raw_result: Dict[str, Any]) -> tuple[List[Dict[str, Any]], str]:
    """
    LangGraph state에서 전달된 reference 정보를 프론트엔드가 기대하는 포맷으로 변환.
    """
    structured = raw_result.get("structured_answer") or {}
    references = structured.get("references") or raw_result.get("sources") or []
    reference_type = structured.get("type") or raw_result.get("type") or "internal"
    formatted = []
    for idx, ref in enumerate(references, 1):
        if isinstance(ref, dict):
            formatted.append(
                {
                    "id": ref.get("id") or idx,
                    "title": ref.get("title") or ref.get("c_id") or f"출처 {idx}",
                    "journal": ref.get("journal") or ref.get("source_spec") or "",
                    "year": ref.get("year") or ref.get("creation_year") or "",
                    "doi": ref.get("doi") or "",
                    "pmid": ref.get("pmid") or ref.get("pubmed") or "",
                    "authors": ref.get("authors") or "",
                }
            )
        else:
            formatted.append(
                {
                    "id": idx,
                    "title": str(ref),
                    "journal": "",
                    "year": "",
                    "doi": "",
                    "pmid": "",
                    "authors": "",
                }
            )
    return formatted, reference_type


def _extract_scores(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph state/structured_answer에서 점수를 추출."""
    structured = raw_result.get("structured_answer") or {}

    def _first(*values):
        for value in values:
            if value is not None:
                return value
        return None

    return {
        "llm_score": _first(structured.get("llm_score"), raw_result.get("llm_score")),
        "relevance_score": _first(
            structured.get("relevance_score"), raw_result.get("relevance_score")
        ),
    }


def _build_history(conversation: ChatConversation) -> list:
    """기존 대화 메시지를 LangChain 메시지 포맷으로 변환."""
    messages = []
    for msg in conversation.messages.order_by("created_at").only("role", "content"):
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
    return messages


def generate_ai_response(conversation: ChatConversation, prompt: str) -> tuple[str, list, dict, str]:
    """
    LangGraph RAG 워크플로우를 호출하여 답변과 참고문헌 정보를 생성한다.
    """
    if _use_fake_backend():
        llm = fake_build()
        history = _build_history(conversation)
        system_prompt = SystemMessage(
            content="당신은 의료 연구 도우미입니다. 한국어로 짧고 명확하게 답변하세요."
        )
        messages = [system_prompt, *history, HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        metadata = getattr(response, "additional_kwargs", {}) or {}
        citations = metadata.get("citations", [])
        return content, citations, {"llm_score": None, "relevance_score": None}, "internal"

    app = _get_graph_app()
    result_state = app.invoke({"question": prompt})
    structured = result_state.get("structured_answer") or {}
    content = (
        result_state.get("final_answer")
        or structured.get("answer")
        or "죄송합니다. 답변을 생성하지 못했습니다."
    )
    citations, reference_type = _format_citations(result_state)
    scores = _extract_scores(result_state)
    return content, citations, scores, reference_type


def summarize_conversation_title(prompt: str) -> str:
    """
    사용자 첫 메시지를 기반으로 대화 타이틀을 요약한다.
    """
    llm = get_llm()
    system_prompt = SystemMessage(
        content="사용자 메시지를 최대 12자 내에서 요약하여 제목을 만들어 주세요. 구체적이고 간결하게."
    )
    messages = [system_prompt, HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    content = response.content if hasattr(response, "content") else str(response)
    return content.strip()[:120] or "새로운 대화"


def generate_concept_graph(message: Message) -> str:
    """
    주어진 AI 응답 메시지를 기반으로 Mermaid 그래프 코드를 생성한다.
    """
    llm = get_llm()
    system_prompt = SystemMessage(
        content=(
            "너는 Mermaid graph 전문가다. "
            "사용자 메시지를 분석해 핵심 개념 간 관계를 flowchart로 표현해라. "
            "항상 ``` 없이 순수한 Mermaid 코드만 반환하고, graph LR 형식을 사용한다."
        )
    )
    user_prompt = HumanMessage(
        content=(
            "다음 AI 응답을 기반으로 주요 개념/원인의 흐름을 Mermaid flowchart로 만들어줘.\n\n"
            f"AI 응답:\n{message.content}"
        )
    )
    response = llm.invoke([system_prompt, user_prompt])
    graph_code = response.content if hasattr(response, "content") else str(response)
    return graph_code.strip()
