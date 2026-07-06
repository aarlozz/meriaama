from django.conf import settings
from django.db import models


class PsychometricTest(models.Model):
    """
    One completed test attempt. `answers` stores raw per-question scores
    as a JSON list (e.g. [0,1,2,3,1,0,2,3,1,0] for PSS-10's 10 items),
    `total_score` and `risk_level` are computed on save.
    """

    class TestType(models.TextChoices):
        PSS10 = "PSS10", "Perceived Stress Scale (10 items)"
        EPDS = "EPDS", "Edinburgh Postnatal Depression Scale"
        GAD7 = "GAD7", "Generalized Anxiety Disorder (7 items)"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MODERATE = "moderate", "Moderate"
        HIGH = "high", "High"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="psychometric_tests")
    test_type = models.CharField(max_length=10, choices=TestType.choices)
    answers = models.JSONField(help_text="Ordered list of per-question integer scores")
    total_score = models.PositiveSmallIntegerField(editable=False)
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices, editable=False)
    taken_at = models.DateTimeField(auto_now_add=True)

    # Cutoffs are simplified for prototype use — cite the validated scale's
    # published cutoffs in your report rather than treating these as clinical fact.
    CUTOFFS = {
        TestType.PSS10: {"moderate": 14, "high": 27},  # PSS-10 range 0-40
        TestType.EPDS: {"moderate": 10, "high": 13},   # EPDS range 0-30
        TestType.GAD7: {"moderate": 5, "high": 10},    # GAD-7 range 0-21
    }

    def compute_risk_level(self):
        cutoffs = self.CUTOFFS[self.test_type]
        if self.total_score >= cutoffs["high"]:
            return self.RiskLevel.HIGH
        if self.total_score >= cutoffs["moderate"]:
            return self.RiskLevel.MODERATE
        return self.RiskLevel.LOW

    def save(self, *args, **kwargs):
        self.total_score = sum(self.answers)
        self.risk_level = self.compute_risk_level()
        super().save(*args, **kwargs)

        # Keep HealthProfile snapshot in sync (safe no-op until that app exists)
        profile = getattr(self.user, "health_profile", None)
        if profile:
            profile.latest_stress_level = self.risk_level
            profile.save(update_fields=["latest_stress_level"])

    def __str__(self):
        return f"{self.test_type} - {self.user.username} - {self.risk_level}"