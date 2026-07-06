from django.conf import settings
from django.db import models


class HealthProfile(models.Model):
    """
    The 'single source of truth' record for a mother. Mood, psychometric,
    and tracker apps read from / write to fields here (via getattr, so
    they stay safe even if this app is added after the others).
    """

    ALLERGY_CHOICES = [
        ("nuts", "Nuts"),
        ("dairy", "Dairy"),
        ("gluten", "Gluten"),
        ("shellfish", "Shellfish"),
        ("eggs", "Eggs"),
        ("soy", "Soy"),
    ]
    DIETARY_CHOICES = [
        ("none", "No restriction"),
        ("vegetarian", "Vegetarian"),
        ("vegan", "Vegan"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="health_profile",
    )

    last_menstrual_period = models.DateField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    current_gestational_week = models.PositiveSmallIntegerField(null=True, blank=True)

    # Updated automatically by mood/psychometric apps -- not user-editable.
    latest_mood_score = models.SmallIntegerField(null=True, blank=True)
    latest_stress_level = models.CharField(max_length=20, blank=True)

    blood_group = models.CharField(max_length=5, blank=True)
    pre_existing_conditions = models.TextField(blank=True)

    # NEW -- used to safety-filter daily wellness/diet suggestions in apps.daily_wellness
    allergies = models.JSONField(default=list, blank=True)  # subset of ALLERGY_CHOICES values
    allergy_other = models.CharField(max_length=200, blank=True)
    has_gestational_diabetes = models.BooleanField(default=False)
    has_hypertension = models.BooleanField(default=False)
    dietary_preference = models.CharField(max_length=20, choices=DIETARY_CHOICES, default="none")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"HealthProfile({self.user.username})"

    def recalculate_gestational_week(self):
        """Call after last_menstrual_period is set/changed."""
        if not self.last_menstrual_period:
            return
        from datetime import date
        days = (date.today() - self.last_menstrual_period).days
        self.current_gestational_week = max(days // 7, 0)
        self.save(update_fields=["current_gestational_week"])