from django.conf import settings
from django.db import models


class PersonalCheckIn(models.Model):
    """A mother's own private note -- never visible to hospital staff."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personal_checkins")
    note = models.TextField()
    image = models.ImageField(upload_to="checkin_images/%Y/%m/", null=True, blank=True)
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


class DoctorQuestion(models.Model):
    """A running checklist of things she wants to ask at her next visit -- private to her."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_questions")
    question = models.CharField(max_length=300)
    is_answered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_answered", "-created_at"]

    def __str__(self):
        return self.question

class WeeklyBabyFact(models.Model):
    """
    Curated, pre-written development content covering a WEEK RANGE (not a
    single exact week) so every week of pregnancy has matching content --
    no gaps, unlike the earlier single-week version.
    """
    start_week = models.PositiveSmallIntegerField()
    end_week = models.PositiveSmallIntegerField()
    size_comparison = models.CharField(max_length=100, blank=True, help_text="e.g. 'about the size of a lime'")
    fact_text = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_week"]

    def __str__(self):
        return f"Weeks {self.start_week}-{self.end_week}"