from django.contrib.auth import views as auth_views
from django.urls import path

from .views import AccountsLoginView, AccountsLogoutView, AccountsRegisterView, ProfileImageUploadView

app_name = "accounts"
urlpatterns = [
    path("login/", AccountsLoginView.as_view(), name="login"),
    path("logout/", AccountsLogoutView.as_view(), name="logout"),
    path("register/", AccountsRegisterView.as_view(), name="register"),
    path("profile-image/", ProfileImageUploadView.as_view(), name="profile-image-upload"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url="/accounts/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url="/accounts/password-reset/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
]
