from django.conf import settings
from django.db import models


class Recommendation(models.Model):
    """Log of every generated answer -- useful for your evaluation chapter."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendations")
    query = models.TextField()
    retrieved_sources = models.JSONField(default=list)  # snapshot of chunks used, for traceability
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Recommendation({self.user.username}, {self.created_at:%Y-%m-%d})"