from __future__ import annotations

from django.utils import timezone

from .models import UserActivityLog


class UserActivityLoggingMiddleware:
    """
    인증된 사용자의 요청 중요 정보를 UserActivityLog에 저장한다.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._log_request(request)
        return response

    def _log_request(self, request):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return

        path = request.path
        if path.startswith("/static") or path.startswith("/.well-known") or path == "/favicon.ico":
            return

        user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]
        ip_addr = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
        if ip_addr and "," in ip_addr:
            ip_addr = ip_addr.split(",")[0].strip()

        UserActivityLog.objects.create(
            user=user,
            path=path,
            method=request.method,
            user_agent=user_agent,
            ip_address=ip_addr,
            created_at=timezone.now(),
        )
