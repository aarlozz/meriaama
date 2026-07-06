from django.conf import settings
from django.db import models


class WeeklyUpdate(models.Model):
    """
    One row per (mother, gestational week). Combines generic educational
    content (fetal_development_note) with clinical data entered by staff
    through the admin panel (weight, blood pressure, notes).

    This app is read-only from the mother's side by design -- the data
    comes from her care team, so writes happen in /admin/ for now (or later
    from a hospital-portal app once you build one).
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_updates")
    gestational_week = models.PositiveSmallIntegerField()

    fetal_development_note = models.TextField(blank=True)
    maternal_changes_note = models.TextField(blank=True)

    maternal_weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    blood_pressure = models.CharField(max_length=15, blank=True)  # e.g. "120/80"
    hospital_notes = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "gestational_week")
        ordering = ["gestational_week"]

    def __str__(self):
        return f"{self.user.username} - week {self.gestational_week}"