from django.db import models
from django.utils import timezone

class DashboardMetric(models.Model):
    """
    대시보드 집계 
    key 예: total_data, active_conversations, monthly_questions, active_users, ai_accuracy_mean, avg_response_time
    """
    key = models.CharField(max_length=100, db_index=True)
    value_num = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    value_text = models.TextField(blank=True)
    delta_num = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)  # +124, +23 … 표시용
    meta = models.JSONField(null=True, blank=True)
    measured_at = models.DateTimeField(default=timezone.now, null=True, db_index=True)

    class Meta:
        ordering = ["-measured_at"]
        constraints = [
            models.UniqueConstraint(fields=["key", "measured_at"], name="uniq_key_measured_at"),
        ]
        indexes = [
            models.Index(fields=["key", "measured_at"]),
            models.Index(fields=["-measured_at"]),
        ]
    def __str__(self):
        return f"{self.key} @ {self.measured_at.isoformat()}"
