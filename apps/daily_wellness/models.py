from django.conf import settings
from django.db import models


class WellnessTip(models.Model):
    """
    One curated, pre-approved tip. `code` is a stable natural key so the
    seed command can be re-run safely (update, not duplicate).

    Safety exclusion/inclusion tags are checked in Python before a tip is
    ever shown or sent to an LLM -- this is what guarantees an allergy or
    condition can never be ignored, regardless of what any AI-generated
    wording does.
    """

    class Category(models.TextChoices):
        NUTRITION = "nutrition", "Nutrition"
        MENTAL_HEALTH = "mental_health", "Mental wellbeing"
        EXERCISE = "exercise", "Movement"
        PRECAUTION = "precaution", "Precaution"

    class Trimester(models.TextChoices):
        FIRST = "first", "First trimester"
        SECOND = "second", "Second trimester"
        THIRD = "third", "Third trimester"
        ALL = "all", "Any stage"

    code = models.SlugField(max_length=50, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    trimester = models.CharField(max_length=10, choices=Trimester.choices)
    text = models.TextField()
    source_name = models.CharField(max_length=100, blank=True)

    avoid_if_allergic_to = models.JSONField(default=list, blank=True)   # e.g. ["nuts", "dairy"]
    avoid_if_condition = models.JSONField(default=list, blank=True)     # e.g. ["gestational_diabetes"]
    avoid_if_diet = models.JSONField(default=list, blank=True)          # e.g. ["vegetarian", "vegan"]
    only_if_condition = models.JSONField(
        default=list, blank=True,
        help_text="If set, tip ONLY shows to mothers with at least one of these conditions (e.g. a gestational-diabetes-specific tip).",
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class DailyWellnessLog(models.Model):
    """
    One generated-and-cached plan per mother per calendar day. Each category
    now holds SEVERAL tips (M2M) instead of exactly one -- upgraded from the
    original single-FK design so the daily plan feels fuller.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_wellness_logs")
    date = models.DateField()

    nutrition_tips = models.ManyToManyField(WellnessTip, blank=True, related_name="+")
    mental_health_tips = models.ManyToManyField(WellnessTip, blank=True, related_name="+")
    exercise_tips = models.ManyToManyField(WellnessTip, blank=True, related_name="+")
    precaution_tips = models.ManyToManyField(WellnessTip, blank=True, related_name="+")

    personalized_text = models.TextField(blank=True)  # Groq-rephrased version; optional, may be empty
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "date")

    def __str__(self):
        return f"{self.user.username} - {self.date}"