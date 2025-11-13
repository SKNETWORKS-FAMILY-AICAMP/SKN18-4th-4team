from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.utils.deprecation import MiddlewareMixin


class DevAutoLoginMiddleware(MiddlewareMixin):
    """
    개발 편의를 위해 DEBUG 모드에서 항상 user001 계정으로 로그인시킨다.
    실제 배포 환경에서는 settings.DEBUG 가 False 이므로 동작하지 않는다.
    """

    USERNAME = "user001"
    PASSWORD = "user1234"
    DEFAULT_EMAIL = "user001@example.com"

    def process_request(self, request):
        if not settings.DEBUG:
            return

        if request.user.is_authenticated:
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=self.USERNAME,
            defaults={"email": self.DEFAULT_EMAIL},
        )
        if created:
            user.set_password(self.PASSWORD)
            user.save()

        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)
