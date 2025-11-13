import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


User = settings.AUTH_USER_MODEL


class ChatConversation(models.Model):
    """
    실제 채팅 세션 단위 모델.
    로그인 사용자는 created_by 로 연결되고, 게스트는 session_key 로 식별한다.
    """

    DEFAULT_TITLE = "새로운 대화"

    title = models.CharField(max_length=255, blank=True, default=DEFAULT_TITLE)
    slug = models.SlugField(max_length=120, unique=True, editable=False)
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_conversations",
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        db_index=True,
        help_text="비로그인 사용자를 위한 세션 키",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_activity_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_message_preview = models.CharField(
        max_length=140,
        blank=True,
        help_text="목록에서 보여줄 마지막 메시지 요약",
    )
    is_archived = models.BooleanField(default=False, db_index=True)
    metadata = models.JSONField(null=True, blank=True)

    # 모델의 메타데이터(옵션, 부가 설정)를 지정
    # ordering, 데이터베이스 인덱스, 테이블 이름 등 설정
    class Meta:
        ordering = ["-last_activity_at", "-created_at"]
        indexes = [
            models.Index(fields=["session_key", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.title or f"Conversation {self.pk}"

    # Helpers -----------------------------------------------------------------
    def save(self, *args, **kwargs):
        if not self.slug:
            base = (self.title or f"conf-{self.uid.hex[:8]}")[:60]
            self.slug = slugify(base) or self.uid.hex[:8]
        if not self.last_activity_at:
            self.last_activity_at = timezone.now()
        super().save(*args, **kwargs)

    def belongs_to(self, user=None, session_key: str | None = None) -> bool:
        if user and user.is_authenticated:
            return self.created_by_id == user.id
        return bool(self.session_key and self.session_key == session_key)

    def update_activity(self, preview: str | None = None):
        """
        메시지가 추가될 때 마지막 활동 시간을 갱신하고 미리보기를 업데이트.
        """
        now = timezone.now()
        self.last_activity_at = now
        self.last_message_at = now
        if preview:
            self.last_message_preview = preview[:140]
        self.save(update_fields=["last_activity_at", "last_message_at", "last_message_preview"])

    @classmethod
    def for_request(cls, request, **kwargs):
        """
        request 객체로부터 사용자/세션을 설정한 Conversation 인스턴스를 생성한다.
        """
        payload = kwargs.copy()
        if request.user.is_authenticated:
            payload.setdefault("created_by", request.user)
        else:
            session_key = request.session.session_key or request.session.save() or request.session.session_key
            payload.setdefault("session_key", session_key)
        return cls.objects.create(**payload)


class Message(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
        ("tool", "Tool"),
    ]
    FEEDBACK_CHOICES = [
        ("positive", "Positive"),
        ("negative", "Negative"),
    ]

    conversation = models.ForeignKey(
        ChatConversation,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Observability & QA
    response_time_ms = models.IntegerField(null=True, blank=True)
    ai_accuracy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    model_name = models.CharField(max_length=120, blank=True)
    tokens_prompt = models.IntegerField(null=True, blank=True)
    tokens_completion = models.IntegerField(null=True, blank=True)

    # RAG/툴/참고문헌
    citations = models.JSONField(null=True, blank=True)  # [{"title":..., "doi":..., "pubmed":...}]
    tool_calls = models.JSONField(null=True, blank=True)  # [{"tool":"pubmed.search", ...}]
    attachments = models.JSONField(null=True, blank=True)  # files/images meta
    metadata = models.JSONField(null=True, blank=True)
    feedback = models.CharField(max_length=10, choices=FEEDBACK_CHOICES, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self):
        return f"{self.role} @ {self.created_at:%Y-%m-%d %H:%M:%S}"

    # Convenience --------------------------------------------------------------
    def set_references(self, references: list | None):
        self.citations = references or []
        self.save(update_fields=["citations"])

    def toggle_feedback(self, value: str | None):
        if value == self.feedback:
            self.feedback = ""
        else:
            self.feedback = value or ""
        self.save(update_fields=["feedback"])
