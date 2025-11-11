import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify

User = settings.AUTH_USER_MODEL

class ChatConversation(models.Model):
    title = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=120, unique=True)
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # 안전한 식별자
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_conversations")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_activity_at = models.DateTimeField(null=True, blank=True, db_index=True,)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_message_preview = models.CharField(max_length=140, blank=True)  # 좌측 목록 미리보기
    is_archived = models.BooleanField(default=False, db_index=True)
    metadata = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ["-last_activity_at", "-created_at"]
        
    # save 메서드는 ChatConversation 인스턴스가 저장될 때 호출
    # slug 필드가 비어 있으면, title이나 uid를 이용해 slug 값을 자동 생성하여 중복 방지
    # 생성된 slug는 사람이 읽기 쉬운 URL의 일부로 사용 가능
    def save(self, *args, **kwargs):
        if not self.slug:
            base = (self.title or f"conf-{self.uid.hex[:8]}")[:60]
            self.slug = slugify(base) or self.uid.hex[:8]
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.title or f"conf-{self.pk}"
    
class Message(models.Model):
    ROLE_CHOICES = [
        ("user", "user"),
        ("assistant", "assistant"),
        ("system", "system"),
        ("tool", "tool"),
    ]
    
    conversation = models.ForeignKey(ChatConversation, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Observability & QA
    response_time_ms = models.IntegerField(null=True, blank=True)
    ai_accuracy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    model_name = models.CharField(max_length=120, blank=True)
    tokens_prompt = models.IntegerField(null=True, blank=True)
    tokens_completion = models.IntegerField(null=True, blank=True)
    
    # RAG/툴/참고문헌
    citations = models.JSONField(null=True, blank=True)   # [{"title":..., "doi":..., "pubmed":...}]
    tool_calls = models.JSONField(null=True, blank=True)  # [{"tool":"pubmed.search", "args":{...}, "result_id":"..."}]
    attachments = models.JSONField(null=True, blank=True) # files/images meta
    
    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]
        
    def __str__(self):
        return f"{self.role} @ {self.created_at}"