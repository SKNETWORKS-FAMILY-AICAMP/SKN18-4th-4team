from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

from .models import CustomUser


def register_user(username: str, email: str, password: str, agreed_terms: bool) -> CustomUser:
    """
    사용자 입력을 받아 CustomUser를 생성한다.
    """

    return CustomUser.objects.create_user(
        name=username,
        email=email,
        password=password,
        agreed_terms=agreed_terms,
    )


def authenticate_user(username: str, password: str) -> CustomUser:
    """
    username/password 조합으로 사용자를 조회하고 검증한다.
    """

    if not CustomUser.objects.filter(name=username).exists():
        raise ValidationError(f"{username}은 존재하지 않는 사용자 아이디입니다.")

    user = authenticate(username=username, password=password)
    if not user:
        raise ValidationError("비밀번호가 올바르지 않습니다.")
    return user
