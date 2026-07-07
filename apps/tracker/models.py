from django.conf import settings
from django.db import models
from django.utils import timezone


class PersonalCheckIn(models.Model):
    """
    A mother's own private note about her pregnancy -- separate from staff-
    entered PrenatalVisit records (apps.hospital_portal.models). Private to
    her; hospital staff never see these.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personal_checkins")
    visit_date = models.DateField(default=timezone.localdate)
    note = models.TextField()
    gestational_week = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-visit_date"]

    def save(self, *args, **kwargs):
        if self._state.adding and self.gestational_week is None:
            profile = getattr(self.user, "health_profile", None)
            if profile and profile.current_gestational_week:
                self.gestational_week = profile.current_gestational_week
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.visit_date}"