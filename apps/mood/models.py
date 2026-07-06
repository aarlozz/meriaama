from django.conf import settings
from django.db import models


class MoodEntry(models.Model):
    """One mood check-in. Multiple per day are allowed -- this tracks how she
    feels *at that moment*, not a single daily summary."""

    class MoodScore(models.IntegerChoices):
        VERY_LOW = 1, "Very low"
        LOW = 2, "Low"
        NEUTRAL = 3, "Neutral"
        GOOD = 4, "Good"
        VERY_GOOD = 5, "Very good"

    # Fixed, pregnancy-relevant tag vocabulary. Kept as simple string choices
    # (not a separate Tag model) since the list is small and unlikely to need
    # per-user customization -- keeps the schema simple for a semester project.
    TAG_CHOICES = [
        ("tired", "Tired"),
        ("anxious", "Anxious"),
        ("nauseous", "Nauseous"),
        ("back_pain", "Back pain"),
        ("irritable", "Irritable"),
        ("hopeful", "Hopeful"),
        ("peaceful", "Peaceful"),
        ("excited", "Excited"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mood_entries")
    score = models.PositiveSmallIntegerField(choices=MoodScore.choices)
    tags = models.JSONField(default=list, blank=True, help_text="List of tag keys, e.g. ['tired', 'anxious']")
    note = models.CharField(max_length=280, blank=True)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-logged_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        profile = getattr(self.user, "health_profile", None)
        if profile:
            profile.latest_mood_score = self.score
            profile.save(update_fields=["latest_mood_score"])

    def tag_labels(self):
        """Convert stored tag keys back to display labels, for templates."""
        lookup = dict(self.TAG_CHOICES)
        return [lookup.get(tag, tag) for tag in self.tags]

    def __str__(self):
        return f"{self.user.username} - {self.score} - {self.logged_at.date()}"