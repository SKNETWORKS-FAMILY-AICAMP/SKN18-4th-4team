import json
from pathlib import Path

from django.shortcuts import render
from django.urls import NoReverseMatch, reverse


QUICK_TEMPLATES_PATH = Path(__file__).resolve().parent / "data" / "quick_templates.json"

def _load_quick_templates():
    """
    빠른 질문 템플릿(quick_templates.json)을 로드하여
    적합하게 정제된 섹션 리스트를 반환합니다.

    - 파일 위치: QUICK_TEMPLATES_PATH
    - 예외 발생 시(파일 없음 또는 JSON 에러): 빈 리스트 반환
    - items 항목이 비어있는 경우 해당 section은 제거
    """
    try:
        with QUICK_TEMPLATES_PATH.open(encoding="utf-8") as fp:
            data = json.load(fp)
    except (FileNotFoundError, json.JSONDecodeError):
        # 파일이 없거나, JSON 파싱 실패 시 빈 리스트 반환
        return []

    sections = data.get("sections", [])
    formatted = []
    # 각 섹션에 대해 items가 비어있지 않은 경우만 필터링 및 정제
    for section in sections:
        items = [item for item in section.get("items", []) if item]
        if items:
            formatted.append(
                {
                    "title": section.get("title", ""),
                    "items": items,
                }
            )
    return formatted

QUICK_TEMPLATE_SECTIONS = _load_quick_templates()


def _safe_reverse(name: str, default: str) -> str:
    """
    주어진 URL name으로 reverse를 시도하고,
    만약 NoReverseMatch 에러가 발생하면 기본값(default) 경로를 반환합니다.
    이는 URL 패턴이 없거나 잘못된 경우에도 안전하게 기본 경로를 사용할 수 있게 해줍니다.
    """
    try:
        return reverse(name)
    except NoReverseMatch:
        return default


def index(request):
    user = request.user
    context = {
        "user_name": (user.get_full_name() or user.get_username() or "게스트 연구자") if user.is_authenticated else "게스트 연구자",
        "user_email": user.email if getattr(user, "email", None) else "research@example.com",
        "main_url": _safe_reverse("main:main", "/main/"),
        "logout_url": _safe_reverse("accounts:logout", "/accounts/logout/"),
        "quick_template_sections": QUICK_TEMPLATE_SECTIONS,
    }
    return render(request, "chat/chat.html", context)
