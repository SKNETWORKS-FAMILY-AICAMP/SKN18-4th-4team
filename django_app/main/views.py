from django.shortcuts import render
from django.urls import NoReverseMatch, reverse


def _safe_reverse(name: str, default: str) -> str:
    try:
        return reverse(name)
    except NoReverseMatch:
        return default


def index(request):
    user = request.user
    context = {
        "user_name": (user.get_full_name() or user.get_username() or "게스트 연구자") if user.is_authenticated else "게스트 연구자",
        "user_email": user.email if getattr(user, "email", None) else "research@example.com",
        "chat_url": _safe_reverse("chat:index", "/chat/"),
        "logout_url": _safe_reverse("accounts:logout", "/accounts/logout/"),
        "show_logout": user.is_authenticated,
    }
    return render(request, "main/main_dashboard.html", context)
