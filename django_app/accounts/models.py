from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models


class CustomUserManager(BaseUserManager):
    """
    기본 User 모델 대신 사용할 CustomUser 생성을 담당한다.
    """

    use_in_migrations = True

    def _validate(self, name: str | None, password: str | None, email: str | None) -> None:
        if not name:
            raise ValueError("name은 필수 항목입니다.")
        if not password or len(password) < 5:
            raise ValueError("password는 필수 항목이면서 최소 5자 이상입니다.")
        try:
            validate_email(email)
        except ValidationError as exc:
            raise ValueError("올바른 이메일 형식이 아닙니다.") from exc

        if self.model.objects.filter(name=name).exists():
            raise ValueError(f"{name}은 이미 존재하는 사용자명입니다.")
        if self.model.objects.filter(email=email).exists():
            raise ValueError(f"{email}은 이미 존재하는 이메일입니다.")

    def create_user(self, name: str, email: str, password: str | None = None, **extra_fields):
        """
        일반 사용자 생성 로직.
        """

        self._validate(name, password, email)
        user = self.model(name=name, email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, name: str, email: str, password: str | None = None, **extra_fields):
        """
        관리자 사용자 생성 로직.
        """

        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(name, email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    프로젝트 전역에서 사용할 사용자 모델.
    """

    objects = CustomUserManager()

    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=500, unique=True)
    profile_image = models.ImageField(upload_to="profile_images/", blank=True, null=True)

    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    agreed_terms = models.BooleanField(default=False)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "name"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "customUser"

    def __str__(self) -> str:
        return self.name

    @property
    def is_staff(self) -> bool:
        return self.is_admin

    def get_full_name(self) -> str:
        return self.name

    def get_short_name(self) -> str:
        return self.name


class UserActivityLog(models.Model):
    """
    인증된 사용자의 요청 활동을 단순히 기록한다.
    """

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="activity_logs")
    path = models.CharField(max_length=512)
    method = models.CharField(max_length=10)
    user_agent = models.CharField(max_length=512, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.name} @ {self.path}"
