from django.conf import settings
from django.db import models


class TrimesterNarrativeCache(models.Model):
    """
    Caches the AI-generated pregnancy narrative so it's only regenerated
    when her visit count actually changes -- not on every page load.
    `narrative_json` holds the structured {overall_progress, trimester_notes,
    positive_signs, things_to_discuss, next_visit_advice} shape. `narrative_text`
    is kept only so any old rows from before this field existed don't error out.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trimester_narrative_cache",
    )
    visit_count_at_generation = models.PositiveIntegerField(default=0)
    narrative_text = models.TextField(blank=True)
    narrative_json = models.JSONField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"TrimesterNarrativeCache({self.user.username})"