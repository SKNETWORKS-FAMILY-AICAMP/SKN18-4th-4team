from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm

from .models import CustomUser

# 이메일 또는 아이디(username)으로 인증할 수 있는 AuthenticationForm 오버라이드
class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    """
    Authentication form that accepts either the username or the email address.
    사용자가 로그인 필드에 이메일이나 사용자명 둘 중 아무거나 입력 가능
    """

    username = forms.CharField(
        label="이메일 또는 사용자명",
        widget=forms.TextInput(attrs={"autofocus": True}),
    )

    def clean(self):
        """
        사용자가 이메일을 입력해도 인증이 정상적으로 작동하도록 처리
        입력값이 이메일 주소라면 대응되는 사용자명의 값으로 변경해서 원래의 AuthenticationForm 로직이 동작
        """
        username = self.cleaned_data.get(self.username_field)
        if username:
            user_model = get_user_model()
            email_field = getattr(user_model, "EMAIL_FIELD", "email")
            email_lookup = {f"{email_field}__iexact": username}

            try:
                # 입력값이 이메일로 일치하는 사용자 찾기
                user = user_model.objects.get(**email_lookup)
            except user_model.DoesNotExist:
                user = None

            if user:
                # 찾았을 경우, username 필드를 해당 계정의 username(여기선 name) 값으로 치환해
                # 최종적으로 AuthenticationForm의 기본 로직이 사용자명으로 인증 처리
                self.cleaned_data[self.username_field] = user.get_username()

        # AuthenticationForm의 원래 clean()을 호출
        return super().clean()

# 사용자 생성을 위한 커스텀 폼 (admin 등에서 사용)
class CustomUserCreationForm(UserCreationForm):
    """
    CustomUser model용 사용자 생성폼 (admin 등에서 사용)
    """
    class Meta:
        model = CustomUser
        fields = ("name", "email")

# 회원가입 화면(FormView 등에서 사용)에서 이용약관 동의 체크박스가 추가된 회원가입 폼
class SignupForm(CustomUserCreationForm):
    """
    회원가입용 사용자 생성폼.
    '이용 약관' 동의 체크박스를 추가로 요구한다.
    """
    agree_terms = forms.BooleanField(
        label="이용 약관에 동의합니다.",
        error_messages={"required": "서비스 이용을 위해 약관에 동의해주세요."},
    )

    class Meta(CustomUserCreationForm.Meta):
        pass

# 사용자 정보 변경 (admin 등에서 사용) 폼
class CustomUserChangeForm(UserChangeForm):
    """
    CustomUser model용 정보 변경 폼 (admin 등에서 사용)
    """
    class Meta:
        model = CustomUser
        fields = (
            "name",
            "email",
            "agreed_terms",
            "is_active",
            "is_admin",
            "is_superuser",
            "groups",
            "user_permissions",
        )
