from django.shortcuts import render
from django.urls import NoReverseMatch, reverse


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
    }
    return render(request, "chat/chat.html", context)
