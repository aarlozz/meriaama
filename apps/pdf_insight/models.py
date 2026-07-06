from django.conf import settings
from django.db import models


def pdf_upload_path(instance, filename):
    return f"pdf_reports/user_{instance.user_id}/{filename}"


class MedicalReport(models.Model):
    """An uploaded lab/medical PDF and its plain-language summary."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="medical_reports")
    file = models.FileField(upload_to=pdf_upload_path)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    summary_text = models.TextField(blank=True)
    flagged_values = models.JSONField(default=list, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Report({self.user.username}, {self.uploaded_at:%Y-%m-%d})"