from django.conf import settings
from django.db import models
from django.utils import timezone


class PrenatalVisit(models.Model):
    """
    One clinical visit, entered by hospital staff. This is the "official"
    record -- the mother sees it read-only on her tracker page alongside
    her own private PersonalCheckIn entries (see apps.tracker.models).

    All clinical fields below are optional on any single visit (a real
    checkup doesn't run every test every time) -- see apps.trimester_analysis
    for the "has this ever been recorded" completeness check across her
    full visit history, and the trend analysis built from whichever fields
    do have data.
    """

    class FetalMovement(models.TextChoices):
        ACTIVE = "active", "Active"
        REDUCED = "reduced", "Reduced"
        NONE = "none", "None reported"

    class UrineLevel(models.TextChoices):
        NEGATIVE = "negative", "Negative"
        TRACE = "trace", "Trace"
        PLUS1 = "plus1", "+1"
        PLUS2 = "plus2", "+2"
        PLUS3 = "plus3", "+3"

    class FetalPosition(models.TextChoices):
        CEPHALIC = "cephalic", "Cephalic (head-down)"
        BREECH = "breech", "Breech"
        TRANSVERSE = "transverse", "Transverse"
        NOT_ASSESSED = "not_assessed", "Not assessed"

    class Edema(models.TextChoices):
        NONE = "none", "None"
        MILD_HANDS_FEET = "mild_hands_feet", "Mild -- hands/feet"
        MILD_FACE = "mild_face", "Mild -- face"
        SEVERE = "severe", "Severe"

    mother = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="prenatal_visits",
        limit_choices_to={"role": "mother"},
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="visits_entered",
        limit_choices_to={"role__in": ["doctor", "nurse", "data_entry"]},
    )
    visit_date = models.DateField(default=timezone.localdate)
    gestational_week = models.PositiveSmallIntegerField(null=True, blank=True)

    # --- The 10 core checkup data points ---
    maternal_weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    blood_pressure = models.CharField(max_length=15, blank=True)  # e.g. "120/80"
    fundal_height_cm = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    fetal_heart_rate_bpm = models.PositiveSmallIntegerField(null=True, blank=True)
    fetal_movement = models.CharField(max_length=10, choices=FetalMovement.choices, blank=True)
    urine_protein = models.CharField(max_length=10, choices=UrineLevel.choices, blank=True)
    urine_glucose = models.CharField(max_length=10, choices=UrineLevel.choices, blank=True)
    hemoglobin_g_dl = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    fetal_position = models.CharField(max_length=15, choices=FetalPosition.choices, blank=True)
    edema = models.CharField(max_length=20, choices=Edema.choices, blank=True)

    doctor_notes = models.TextField(blank=True)
    next_visit_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-visit_date"]

    def save(self, *args, **kwargs):
        if self._state.adding and self.gestational_week is None:
            profile = getattr(self.mother, "health_profile", None)
            if profile and profile.current_gestational_week:
                self.gestational_week = profile.current_gestational_week
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.mother.username} - {self.visit_date} (week {self.gestational_week})"


# Field names + labels used both for the completeness checklist (staff side)
# and for picking which fields to analyze on the Trimester Analysis page.
TRACKED_FIELDS = [
    ("maternal_weight_kg", "Maternal weight"),
    ("blood_pressure", "Blood pressure"),
    ("fundal_height_cm", "Fundal height"),
    ("fetal_heart_rate_bpm", "Fetal heart rate"),
    ("fetal_movement", "Fetal movement"),
    ("urine_protein", "Urine protein"),
    ("urine_glucose", "Urine glucose"),
    ("hemoglobin_g_dl", "Hemoglobin"),
    ("fetal_position", "Fetal position"),
    ("edema", "Edema/swelling"),
]


class Medication(models.Model):
    """
    A prescribed course of medication. Staff-entered, same trust model as
    PrenatalVisit. Adherence (whether she actually took each dose) is
    tracked separately in apps.tracker.models.MedicationLog -- mirrors the
    existing PrenatalVisit (staff) / PersonalCheckIn (mother) split.
    """
    mother = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="medications", limit_choices_to={"role": "mother"},
    )
    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="medications_prescribed",
    )
    visit = models.ForeignKey(
        PrenatalVisit, on_delete=models.SET_NULL, null=True, blank=True, related_name="medications",
    )

    name = models.CharField(max_length=150)
    dosage = models.CharField(max_length=50, help_text="e.g. 500mg")
    frequency_per_day = models.PositiveSmallIntegerField(default=1)
    duration_days = models.PositiveSmallIntegerField()
    start_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    @property
    def end_date(self):
        from datetime import timedelta
        return self.start_date + timedelta(days=self.duration_days - 1)

    @property
    def is_active(self):
        today = timezone.localdate()
        return self.start_date <= today <= self.end_date

    @property
    def day_number(self):
        today = timezone.localdate()
        raw = (today - self.start_date).days + 1
        return max(min(raw, self.duration_days), 0)

    @property
    def expected_doses_so_far(self):
        return min(max(self.day_number, 0), self.duration_days) * self.frequency_per_day

    @property
    def total_expected_doses(self):
        return self.duration_days * self.frequency_per_day

    @property
    def taken_doses_count(self):
        return self.logs.count()

    @property
    def adherence_percent(self):
        expected = self.expected_doses_so_far
        if expected <= 0:
            return 0
        return min(round(self.taken_doses_count / expected * 100), 100)

    def __str__(self):
        return f"{self.name} ({self.mother.username})"