from django.conf import settings
from django.db import models
from datetime import date, timedelta


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
    COMPLICATION_CHOICES = [
        ("miscarriage", "Miscarriage or pregnancy loss"),
        ("preterm_birth", "Early (preterm) birth"),
        ("c_section", "C-section (cesarean delivery)"),
        ("stillbirth", "Stillbirth"),
        ("other", "Something else"),
    ]
    BLOOD_GROUP_CHOICES = [
        ("", "Select your blood group"),
        ("A+", "A+"), ("A-", "A-"),
        ("B+", "B+"), ("B-", "B-"),
        ("AB+", "AB+"), ("AB-", "AB-"),
        ("O+", "O+"), ("O-", "O-"),
        ("unknown", "I don't know"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="health_profile",
    )

    last_menstrual_period = models.DateField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    edd_is_manual_override = models.BooleanField(default=False)
    current_gestational_week = models.PositiveSmallIntegerField(null=True, blank=True)

    latest_mood_score = models.SmallIntegerField(null=True, blank=True)
    latest_stress_level = models.CharField(max_length=20, blank=True)

    blood_group = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES, blank=True)
    pre_existing_conditions = models.TextField(blank=True)

    allergies = models.JSONField(default=list, blank=True)
    allergy_other = models.CharField(max_length=200, blank=True)
    has_gestational_diabetes = models.BooleanField(default=False)
    has_hypertension = models.BooleanField(default=False)
    dietary_preference = models.CharField(max_length=20, choices=DIETARY_CHOICES, default="none")

    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    previous_pregnancies_count = models.PositiveSmallIntegerField(default=0)
    live_births_count = models.PositiveSmallIntegerField(default=0)
    previous_complications = models.JSONField(default=list, blank=True)
    previous_complications_other = models.CharField(max_length=200, blank=True)
    smokes = models.BooleanField(default=False)
    drinks_alcohol = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"HealthProfile({self.user.username})"

    def recalculate_derived_dates(self):
        if not self.last_menstrual_period:
            return
        days = (date.today() - self.last_menstrual_period).days
        self.current_gestational_week = max(days // 7, 0)
        update_fields = ["current_gestational_week"]
        if not self.edd_is_manual_override:
            self.expected_delivery_date = self.last_menstrual_period + timedelta(days=280)
            update_fields.append("expected_delivery_date")
        self.save(update_fields=update_fields)

    @property
    def weeks_until_due(self):
        if not self.expected_delivery_date:
            return None
        days_left = (self.expected_delivery_date - date.today()).days
        return max(days_left // 7, 0) if days_left >= 0 else None

    @property
    def is_first_pregnancy(self):
        return self.previous_pregnancies_count == 0