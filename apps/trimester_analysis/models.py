from django.conf import settings
from django.db import models


class TrimesterNarrativeCache(models.Model):
    """
    Caches the Groq-generated narrative so it's only regenerated when her
    visit count actually changes -- not on every page load.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trimester_narrative_cache")
    visit_count_at_generation = models.PositiveIntegerField(default=0)
    narrative_text = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now=True)
