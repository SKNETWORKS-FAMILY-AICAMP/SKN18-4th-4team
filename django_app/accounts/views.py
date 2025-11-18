from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, View

from .forms import EmailOrUsernameAuthenticationForm, SignupForm
from .service import authenticate_user, register_user


class AccountsLoginView(FormView):
    """
    Custom login view that mirrors the bespoke MedAI UI.
    """

    template_name = "accounts/login.html"
    form_class = EmailOrUsernameAuthenticationForm
    success_url = reverse_lazy("main:index")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("main:index")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password")
        try:
            user = authenticate_user(username, password)
        except ValidationError as exc:
            form.add_error(None, exc.message)
            return self.form_invalid(form)

        login(self.request, user)
        remember_me = self.request.POST.get("remember_me") == "on"
        self.request.session.set_expiry(1209600 if remember_me else 0)
        return super().form_valid(form)


class AccountsLogoutView(View):
    """
    Simple logout view that handles GET requests explicitly.
    """

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("accounts:login")


class AccountsRegisterView(FormView):
    """
    간단한 회원가입 뷰. 가입 성공 시 로그인 페이지로 이동한다.
    """

    template_name = "accounts/register.html"
    form_class = SignupForm
    success_url = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("main:index")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            register_user(
                username=form.cleaned_data["name"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password1"],
                agreed_terms=form.cleaned_data.get("agree_terms", False),
            )
        except (ValidationError, ValueError) as exc:
            form.add_error(None, getattr(exc, "message", str(exc)))
            return self.form_invalid(form)

        messages.success(self.request, "회원가입이 완료되었습니다. 로그인해주세요.")
        return super().form_valid(form)


class ProfileImageUploadView(View):
    """
    Handles AJAX uploads for user profile images.
    """

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

        uploaded_file = request.FILES.get("profile_image")
        if not uploaded_file:
            return JsonResponse({"error": "업로드할 이미지를 선택해주세요."}, status=400)

        if uploaded_file.size > 5 * 1024 * 1024:
            return JsonResponse({"error": "이미지 크기는 5MB 이하여야 합니다."}, status=400)

        user = request.user
        if user.profile_image:
            user.profile_image.delete(save=False)
        user.profile_image.save(uploaded_file.name, uploaded_file, save=True)
        image_url = request.build_absolute_uri(user.profile_image.url)

        return JsonResponse({"message": "프로필 이미지가 저장되었습니다.", "image_url": image_url})
