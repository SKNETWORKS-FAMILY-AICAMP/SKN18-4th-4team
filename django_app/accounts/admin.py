from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import CustomUser

# CustomUser 모델을 효과적으로 관리할 수 있도록 설정을 제공하는 어드민 클래스
# add_form 및 form을 지정하여 사용자 추가와 수정 폼을 지정
# list_display, list_filter, search_fields, ordering 등을 통해 관리자 목록에서의 표시/정렬/검색 필드를 지정
# fieldsets와 add_fieldsets는 입력 폼에서의 필드 배치와 구조를 설정
# readonly_fields는 읽기 전용 필드로, 편집이 불가능한 필드를 지정
@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ("id", "name", "email", "agreed_terms", "is_admin", "is_active")
    list_filter = ("agreed_terms", "is_admin", "is_active")
    search_fields = ("name", "email")
    ordering = ("id",)
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("name", "email", "password")}),
        ("권한", {"fields": ("is_active", "is_admin", "is_superuser", "groups", "user_permissions", "agreed_terms")}),
        ("메타데이터", {"fields": ("last_login", "created_on", "updated_on")}),
    )
    readonly_fields = ("last_login", "created_on", "updated_on")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("name", "email", "password1", "password2", "is_admin", "is_active", "agreed_terms"),
            },
        ),
    )
