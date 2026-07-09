from django.conf import settings
from django.db import models


class PersonalCheckIn(models.Model):
    """A mother's own private note -- never visible to hospital staff."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personal_checkins")
    note = models.TextField()
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-logged_at"]

    def __str__(self):
        return f"{self.user.username} - {self.logged_at:%Y-%m-%d}"


class MedicationLog(models.Model):
    """One 'I took a dose' tap against a prescribed Medication (hospital_portal)."""
    medication = models.ForeignKey("hospital_portal.Medication", on_delete=models.CASCADE, related_name="logs")
    date = models.DateField()
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-logged_at"]

    def __str__(self):
        return f"{self.medication.name} - {self.date}"