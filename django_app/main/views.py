from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse

from chat.models import Message


def _safe_reverse(name: str, default: str) -> str:
    try:
        return reverse(name)
    except NoReverseMatch:
        return default


@login_required(login_url="accounts:login")
def index(request):
    user = request.user
    message_qs = Message.objects.filter(conversation__is_archived=False, role="assistant")
    feedback_total = message_qs.exclude(feedback="").count()
    positive_feedback = message_qs.filter(feedback="positive").count()
    ai_accuracy = (positive_feedback / feedback_total * 100) if feedback_total else 0

    relevance_avg = (
        message_qs.filter(relevance_score__isnull=False).aggregate(avg=Avg("relevance_score"))["avg"] or 0
    )

    internal_q = Q(reference_type="internal") | Q(reference_type__isnull=True) | Q(reference_type="")
    internal_count = message_qs.filter(internal_q).count()
    external_count = message_qs.filter(reference_type="external").count()
    reference_total = internal_count + external_count
    internal_ratio = (internal_count / reference_total * 100) if reference_total else 0
    external_ratio = (external_count / reference_total * 100) if reference_total else 0

    dashboard_stats = {
        "total_papers": 9686,
        "total_research_questions": message_qs.count(),
        "ai_answer_accuracy": ai_accuracy,
        "rag_matching_rate": relevance_avg,
        "internal_usage_rate": internal_ratio,
        "external_usage_rate": external_ratio,
    }

    user_avatar_url = ""
    if getattr(user, "profile_image", None):
        try:
            if user.profile_image:
                user_avatar_url = user.profile_image.url
        except ValueError:
            user_avatar_url = ""

    context = {
        "user_name": (user.get_full_name() or user.get_username() or "게스트 연구자") if user.is_authenticated else "게스트 연구자",
        "user_email": user.email if getattr(user, "email", None) else "research@example.com",
        "chat_url": _safe_reverse("chat:index", "/chat/"),
        "logout_url": _safe_reverse("accounts:logout", "/accounts/logout/"),
        "show_logout": user.is_authenticated,
        "user_avatar_url": user_avatar_url,
        "profile_upload_url": _safe_reverse("accounts:profile-image-upload", ""),
        "dashboard_stats": dashboard_stats,
    }
    return render(request, "main/main_dashboard.html", context)
