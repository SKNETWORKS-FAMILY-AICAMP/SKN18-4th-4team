from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

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
    payload = {
        "question": prompt,
        "conversation_id": str(conversation.id),
    }
    result_state = app.invoke(payload)
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


def _clean_question_text(text: str) -> str:
    """
    Remove wrapping 기호/따옴표 등을 정리하고 의미 없는 토큰은 빈 문자열로 반환.
    """
    if text is None:
        return ""
    cleaned = str(text).strip()
    if not cleaned:
        return ""
    # remove trailing commas/brackets commonly returned by code blocks
    cleaned = cleaned.strip(",")
    cleaned = cleaned.strip()

    if cleaned.startswith("["):
        cleaned = cleaned.lstrip("[ ")
    if cleaned.endswith("]"):
        cleaned = cleaned.rstrip("] ")

    def _strip_matching_quotes(value: str) -> str:
        while len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'", "`"}:
            value = value[1:-1].strip()
        return value

    cleaned = _strip_matching_quotes(cleaned)
    cleaned = cleaned.strip()

    junk_tokens = {"", "[", "]", "[,", ",]", "json", "```json", "```", "`json", "`"}
    if cleaned.lower() in junk_tokens:
        return ""
    if cleaned.startswith("```") or cleaned.endswith("```"):
        return ""
    return cleaned


def _normalize_questions(raw: str) -> List[str]:
    """
    LLM 응답 문자열을 안전하게 파싱하여 질문 리스트로 변환.
    """
    questions: List[str] = []
    cleaned = (raw or "").strip()
    if not cleaned:
        return questions

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict):
        # {"questions": [...]} 또는 {"items": [...]} 형태 지원
        for key in ("questions", "items", "data"):
            if key in data and isinstance(data[key], Sequence):
                data = data[key]
                break

    if isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
        for item in data:
            if isinstance(item, str):
                text = item.strip()
            elif isinstance(item, dict):
                text = (
                    item.get("question")
                    or item.get("text")
                    or item.get("value")
                    or ""
                )
                text = text.strip()
            else:
                text = str(item).strip()
            cleaned_text = _clean_question_text(text)
            if cleaned_text:
                questions.append(cleaned_text)
        if questions:
            return _dedupe_limit(questions)

    # JSON 파싱 실패 시 라인 나누기 방식
    for line in cleaned.replace("\r", "\n").split("\n"):
        candidate = line.strip()
        if not candidate:
            continue
        # "- 1. 질문" 형태 정규화
        candidate = candidate.lstrip("-*•0123456789.) ").strip()
        candidate = _clean_question_text(candidate)
        if candidate:
            questions.append(candidate)
        if len(questions) >= 6:
            break
    return _dedupe_limit(questions)


def _dedupe_limit(items: List[str], limit: int = 3) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def generate_related_questions(message: Message) -> List[str]:
    """
    AI 응답 메시지를 기반으로 MemorySaver에 도움이 되는 연관 질문을 생성.
    """
    llm = get_llm()
    system_prompt = SystemMessage(
        content=(
            "너는 의료 연구 대화를 이어가는 연관 질문 전문가다. "
            "주어진 AI 응답 내용을 이해하고, MemorySaver 노드가 맥락을 축적할 수 있도록 "
            "핵심 정보(질병, 연구대상, 한계점, 다음 단계)를 구체적으로 참조한 한국어 질문 3개를 만들어라. "
            "임상시험, 치료법, 근거 데이터 등 답변에 언급된 세부 사항을 활용하라. "
            "반드시 JSON 배열 문자열만 출력하고, 각 항목은 짧고 행동지향적인 하나의 질문 문장이어야 한다."
        )
    )
    user_prompt = HumanMessage(
        content=(
            "다음 AI 응답을 참고하여 연관 질문 3개를 만들어 주세요. "
            "각 질문은 서로 다른 시각을 제공하고, 후속 대화에서 기억 관리가 쉬운 형태여야 합니다.\n\n"
            f"AI 응답:\n{message.content}"
        )
    )
    response = llm.invoke([system_prompt, user_prompt])
    raw_content = response.content if hasattr(response, "content") else str(response)
    questions = _normalize_questions(raw_content)
    return questions[:3]
