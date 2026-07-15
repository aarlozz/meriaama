from django.conf import settings
from django.db import models
from django.db.models import Q


class DoctorAssignment(models.Model):
    """
    Links one mother to one doctor for chat. Only one ACTIVE assignment per
    mother at a time (enforced at the DB level) -- reassigning creates a
    new row and deactivates the old one, keeping history instead of
    deleting it.
    """
    mother = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="doctor_assignments", limit_choices_to={"role": "mother"},
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="assigned_mothers", limit_choices_to={"role": "doctor"},
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="assignments_made",
    )
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["mother"], condition=Q(is_active=True),
                name="unique_active_assignment_per_mother",
            )
        ]

    def __str__(self):
        return f"{self.mother.username} -> Dr. {self.doctor.username}"


class ChatMessage(models.Model):
    assignment = models.ForeignKey(DoctorAssignment, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.text[:30]}"