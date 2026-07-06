from django.conf import settings
from django.db import models


class ClinicalRecord(models.Model):
    """
    Entered by doctors/nurses/data-entry staff via Django admin
    (role-restricted, see admin.py). On save, pushes relevant fields into
    the mother's WeeklyUpdate and HealthProfile so the mobile app reflects
    it immediately -- this is the "real-time sync" described in the report.
    """
    mother = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clinical_records",
        limit_choices_to={"role": "mother"},
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="records_entered",
        limit_choices_to={"role__in": ["doctor", "nurse", "data_entry"]},
    )
    gestational_week = models.PositiveSmallIntegerField()
    maternal_weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    blood_pressure = models.CharField(max_length=15, blank=True)
    ultrasound_notes = models.TextField(blank=True)
    appointment_notes = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.mother.username} - week {self.gestational_week} (by {self.entered_by})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_to_tracker()

    def _sync_to_tracker(self):
        from apps.tracker.models import WeeklyUpdate
        update, _ = WeeklyUpdate.objects.get_or_create(
            user=self.mother, gestational_week=self.gestational_week
        )
        update.maternal_weight_kg = self.maternal_weight_kg
        update.blood_pressure = self.blood_pressure
        update.hospital_notes = self.appointment_notes or self.ultrasound_notes
        update.save()
