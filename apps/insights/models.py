from django.db import models


class InsightSuggestion(models.Model):
    """
    A curated, pre-written suggestion shown when a specific condition is
    detected in her mood/stress-test data. No LLM involved -- conditions
    are detected by plain Python rules (see rules.py), then matched against
    this pool. Admin-editable via /admin/, seeded from a JSON fixture.
    """

    class Condition(models.TextChoices):
        MOOD_DIP = "mood_dip", "Mood has dipped"
        MOOD_IMPROVED = "mood_improved", "Mood has improved"
        MOOD_STABLE = "mood_stable", "Mood is steady"
        NO_RECENT_MOOD_LOG = "no_recent_mood_log", "Hasn't logged mood recently"
        NO_STRESS_TEST_TAKEN = "no_stress_test_taken", "Never taken a stress test"
        STRESS_TEST_OVERDUE = "stress_test_overdue", "Stress test overdue"
        HIGH_RISK_LATEST = "high_risk_latest", "Latest test showed high risk"
        MODERATE_RISK_LATEST = "moderate_risk_latest", "Latest test showed moderate risk"
        WORSENING_RISK_TREND = "worsening_risk_trend", "Risk trending upward across tests"
        CONSISTENT_LOGGING = "consistent_logging", "Logging consistently"
        GENERAL = "general", "General / fallback"

    class ActionTarget(models.TextChoices):
        MOOD = "mood-checkin", "Mood Check-in"
        PSYCHOMETRIC = "psychometric-select", "Stress Test"
        DAILY_PLAN = "daily-plan", "Today's Wellness Plan"
        WELLNESS_CHAT = "wellness-chat", "Ask Meri Aama"
        FORUM = "forum-list", "Community Forum"
        NONE = "", "No link"

    code = models.SlugField(max_length=60, unique=True)
    condition = models.CharField(max_length=30, choices=Condition.choices)
    severity = models.CharField(
        max_length=10,
        choices=[("info", "Info"), ("caution", "Caution"), ("positive", "Positive")],
        default="info",
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    action_target = models.CharField(max_length=30, choices=ActionTarget.choices, blank=True)
    action_label = models.CharField(max_length=60, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["condition"]

    def __str__(self):
        return self.code
