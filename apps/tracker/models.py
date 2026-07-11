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

from django.db import models

from django.db import models


from django.db import models


class WeeklyBabyFact(models.Model):
    """
    Educational pregnancy development content shown on the Pregnancy Tracker.
    """

    TRIMESTER_CHOICES = (
        (1, "First Trimester"),
        (2, "Second Trimester"),
        (3, "Third Trimester"),
    )

    start_week = models.PositiveSmallIntegerField(help_text="Starting gestational week")
    end_week = models.PositiveSmallIntegerField(help_text="Ending gestational week")
    trimester = models.PositiveSmallIntegerField(choices=TRIMESTER_CHOICES)
    title = models.CharField(max_length=200, help_text="Dashboard heading")
    size_comparison = models.CharField(max_length=100, help_text="Example: About the size of an avocado")
    average_length_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    average_weight_g = models.PositiveIntegerField(null=True, blank=True)
    image_name = models.CharField(max_length=100, blank=True, help_text="Example: week24.png")

    # Changed from TextField -> JSONField: the seed data provides these
    # as lists of bullet points, not single paragraphs.
    baby_development = models.JSONField(default=list, blank=True, help_text="List of developmental milestones")
    mother_changes = models.JSONField(default=list, blank=True, help_text="List of maternal body changes")
    warning_signs = models.JSONField(default=list, blank=True, help_text="List of symptoms requiring medical care")

    nutrition_tip = models.TextField(blank=True)
    exercise_tip = models.TextField(blank=True)
    weekly_milestone = models.CharField(max_length=250, blank=True)
    fun_fact = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_week"]
        verbose_name = "Weekly Baby Development"
        verbose_name_plural = "Weekly Baby Development"

    def __str__(self):
        return f"Weeks {self.start_week}-{self.end_week}"