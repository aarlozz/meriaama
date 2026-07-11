from django.conf import settings
from django.db import models


class Recommendation(models.Model):
    """Log of every generated answer -- useful for your evaluation chapter."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendations")
    query = models.TextField()
    retrieved_sources = models.JSONField(default=list)
    response_text = models.TextField()  # kept for backward compatibility with rows created before this update
    structured_response = models.JSONField(null=True, blank=True)  # NEW -- {summary, key_points, sources_used}
    safety_flags = models.JSONField(default=list, blank=True)  # NEW -- allergen mentions detected in the answer
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Recommendation({self.user.username}, {self.created_at:%Y-%m-%d})"