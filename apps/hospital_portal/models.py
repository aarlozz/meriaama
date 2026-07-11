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


from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Medication(models.Model):
    """
    A prescribed course of medication entered by hospital staff.

    Doctors prescribe the medication while mothers record whether they
    actually took each dose through MedicationLog in the tracker app.

    This follows the same trust model as PrenatalVisit:
        • Hospital staff -> prescription
        • Mother -> adherence
    """

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    mother = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="medications",
        limit_choices_to={"role": "mother"},
    )

    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="medications_prescribed",
    )

    visit = models.ForeignKey(
        "hospital_portal.PrenatalVisit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medications",
    )

    # ------------------------------------------------------------------
    # Choices
    # ------------------------------------------------------------------

    MEDICATION_TYPE_CHOICES = [
        ("supplement", "Supplement"),
        ("vitamin", "Vitamin"),
        ("antibiotic", "Antibiotic"),
        ("painkiller", "Pain Relief"),
        ("other", "Other"),
    ]

    ROUTE_CHOICES = [
        ("oral", "Oral"),
        ("injection", "Injection"),
        ("iv", "Intravenous"),
        ("topical", "Topical"),
        ("other", "Other"),
    ]

    TIME_CHOICES = [
        ("morning", "Morning"),
        ("afternoon", "Afternoon"),
        ("evening", "Evening"),
        ("night", "Night"),
        ("custom", "Custom Time"),
    ]

    FOOD_CHOICES = [
        ("before", "Before Food"),
        ("after", "After Food"),
        ("with", "With Food"),
        ("empty", "Empty Stomach"),
        ("any", "Any Time"),
    ]

    # ------------------------------------------------------------------
    # Medication Information
    # ------------------------------------------------------------------

    name = models.CharField(
        max_length=150,
        help_text="Medication name (e.g. Ferrous Sulfate)",
    )

    dosage = models.CharField(
        max_length=50,
        help_text="e.g. 500 mg, 5 mL",
    )

    medication_type = models.CharField(
        max_length=20,
        choices=MEDICATION_TYPE_CHOICES,
        default="supplement",
    )

    purpose = models.CharField(
        max_length=200,
        blank=True,
        help_text="Reason for prescribing (e.g. Iron deficiency)",
    )

    route = models.CharField(
        max_length=20,
        choices=ROUTE_CHOICES,
        default="oral",
    )

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------

    frequency_per_day = models.PositiveSmallIntegerField(
        default=1,
        help_text="Number of doses per day",
    )

    medicine_time = models.CharField(
        max_length=20,
        choices=TIME_CHOICES,
        default="morning",
    )

    reminder_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Optional reminder time",
    )

    food_instruction = models.CharField(
        max_length=20,
        choices=FOOD_CHOICES,
        default="after",
    )

    duration_days = models.PositiveSmallIntegerField()

    start_date = models.DateField(
        default=timezone.localdate,
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional instructions from the doctor",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    # ------------------------------------------------------------------
    # Computed Properties
    # ------------------------------------------------------------------

    @property
    def end_date(self):
        return self.start_date + timedelta(days=self.duration_days - 1)

    @property
    def is_active(self):
        today = timezone.localdate()
        return self.start_date <= today <= self.end_date

    @property
    def days_remaining(self):
        if not self.is_active:
            return 0
        return (self.end_date - timezone.localdate()).days + 1

    @property
    def day_number(self):
        today = timezone.localdate()
        raw = (today - self.start_date).days + 1
        return max(min(raw, self.duration_days), 0)

    @property
    def expected_doses_so_far(self):
        return (
            min(max(self.day_number, 0), self.duration_days)
            * self.frequency_per_day
        )

    @property
    def total_expected_doses(self):
        return self.duration_days * self.frequency_per_day

    @property
    def taken_doses_count(self):
        return self.logs.count()

    @property
    def missed_doses(self):
        return max(
            self.expected_doses_so_far - self.taken_doses_count,
            0,
        )

    @property
    def adherence_percent(self):
        expected = self.expected_doses_so_far

        if expected <= 0:
            return 0

        return min(
            round((self.taken_doses_count / expected) * 100),
            100,
        )

    @property
    def status(self):
        """
        Overall medication status.
        """

        if not self.is_active:
            return "completed"

        if self.adherence_percent >= 90:
            return "excellent"

        if self.adherence_percent >= 70:
            return "good"

        return "needs_attention"

    def __str__(self):
        return f"{self.name} ({self.mother.username})"