"""
anc_clinical/models.py

Everything here is genuinely NEW functionality -- none of it duplicates
hospital_portal. Each model hangs off hospital_portal.PrenatalVisit (the
one canonical visit record) via ForeignKey, so there's a single source of
truth for "what happened at this checkup."

LabResult.save() and UltrasoundReport.save() both call into flag_engine at
write time so `is_flagged` is always correct without a signal round-trip
(they're not FK'd *from* PrenatalVisit's own save(), so no risk of the
recursion that PrenatalVisit's own flagging needs a signal to avoid).
"""
from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# 1. Reference table -- keeps clinical thresholds data-driven, not hardcoded
# ---------------------------------------------------------------------------
class LabTestReference(models.Model):
    TRIMESTER_CHOICES = [
        (0, "Any"),
        (1, "1st Trimester"),
        (2, "2nd Trimester"),
        (3, "3rd Trimester"),
    ]

    test_code = models.CharField(max_length=50)   # e.g. "HB", "TSH", "BP_SYSTOLIC"
    test_name = models.CharField(max_length=150)
    unit = models.CharField(max_length=30, blank=True)
    trimester = models.IntegerField(choices=TRIMESTER_CHOICES, default=0)

    normal_min = models.FloatField(null=True, blank=True)
    normal_max = models.FloatField(null=True, blank=True)
    severe_min = models.FloatField(null=True, blank=True)
    severe_max = models.FloatField(null=True, blank=True)

    flag_message_low = models.CharField(max_length=255, blank=True)
    flag_message_high = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("test_code", "trimester")
        verbose_name = "Lab Test Reference Range"

    def __str__(self):
        return f"{self.test_name} (T{self.trimester or 'Any'})"

    def evaluate(self, value):
        """Returns (is_flagged: bool, severity: str, reason: str)."""
        if value is None:
            return False, "", ""
        if self.severe_min is not None and value < self.severe_min:
            return True, "severe", self.flag_message_low or f"{self.test_name} critically low"
        if self.severe_max is not None and value > self.severe_max:
            return True, "severe", self.flag_message_high or f"{self.test_name} critically high"
        if self.normal_min is not None and value < self.normal_min:
            return True, "moderate", self.flag_message_low or f"{self.test_name} below normal range"
        if self.normal_max is not None and value > self.normal_max:
            return True, "moderate", self.flag_message_high or f"{self.test_name} above normal range"
        return False, "normal", ""


# ---------------------------------------------------------------------------
# 2. Lab results -- FK to the EXISTING PrenatalVisit, not a new visit model
# ---------------------------------------------------------------------------
class LabResult(models.Model):
    visit = models.ForeignKey(
        "hospital_portal.PrenatalVisit", on_delete=models.CASCADE, related_name="lab_results"
    )
    test_code = models.CharField(max_length=50)     # matches LabTestReference.test_code
    test_name = models.CharField(max_length=150)
    value_numeric = models.FloatField(null=True, blank=True)
    value_text = models.CharField(max_length=100, blank=True)  # "Reactive", "+1", "O+" etc
    unit = models.CharField(max_length=30, blank=True)

    is_flagged = models.BooleanField(default=False)
    severity = models.CharField(max_length=10, blank=True)   # normal / moderate / severe
    flag_reason = models.CharField(max_length=255, blank=True)

    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["test_code"])]

    def save(self, *args, **kwargs):
        # Lazy import -- avoids a circular import at app-load time, since
        # flag_engine also needs to import LabTestReference from this file.
        from apps.anc_clinical.flag_engine import evaluate_lab_result

        trimester = 0
        if self.visit_id and getattr(self.visit, "gestational_week", None):
            week = self.visit.gestational_week
            trimester = 1 if week <= 13 else 2 if week <= 27 else 3

        flagged, severity, reason = evaluate_lab_result(
            self.test_code, trimester, self.value_numeric, self.value_text
        )
        self.is_flagged = flagged
        self.severity = severity
        self.flag_reason = reason
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.test_name}: {self.value_numeric or self.value_text}"


# ---------------------------------------------------------------------------
# 3. Ultrasound reports -- FK to PrenatalVisit
# ---------------------------------------------------------------------------
class UltrasoundReport(models.Model):
    SCAN_TYPE = [
        ("dating", "Dating / Viability Scan (6-9 wks)"),
        ("nt_dual", "NT Scan + Dual Marker (11-13+6 wks)"),
        ("anomaly", "Anomaly Scan / TIFFA (18-22 wks)"),
        ("growth", "Growth Scan (28+ wks)"),
    ]

    visit = models.ForeignKey(
        "hospital_portal.PrenatalVisit", on_delete=models.CASCADE, related_name="ultrasound_reports"
    )
    scan_type = models.CharField(max_length=20, choices=SCAN_TYPE)
    scan_date = models.DateField()

    # Dating scan
    intrauterine_confirmed = models.BooleanField(null=True, blank=True)
    number_of_fetuses = models.PositiveIntegerField(null=True, blank=True)
    fetal_cardiac_activity = models.BooleanField(null=True, blank=True)

    # NT + dual marker
    nuchal_translucency_mm = models.FloatField(null=True, blank=True)
    dual_marker_risk = models.CharField(max_length=20, blank=True)  # "low" / "high"

    # Anomaly / growth
    placenta_position = models.CharField(max_length=100, blank=True)
    liquor_status = models.CharField(max_length=100, blank=True)  # normal/oligo/poly
    head_circumference_mm = models.FloatField(null=True, blank=True)
    abdominal_circumference_mm = models.FloatField(null=True, blank=True)
    femur_length_mm = models.FloatField(null=True, blank=True)
    estimated_gestational_age_weeks = models.FloatField(null=True, blank=True)
    estimated_fetal_weight_g = models.FloatField(null=True, blank=True)
    estimated_fetal_weight_percentile = models.FloatField(
        null=True, blank=True,
        help_text="If known -- used to flag growth restriction (<10th percentile)",
    )
    fetal_movement_normal = models.BooleanField(null=True, blank=True)

    notes = models.TextField(blank=True)
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.CharField(max_length=255, blank=True)

    def clean(self):
        reasons = []

        if self.scan_type == "dating":
            if self.intrauterine_confirmed is False:
                reasons.append("Intrauterine pregnancy not confirmed")
            if self.fetal_cardiac_activity is False:
                reasons.append("No fetal cardiac activity detected")
            if self.number_of_fetuses is not None and self.number_of_fetuses > 4:
                reasons.append(f"Number of fetuses ({self.number_of_fetuses}) is clinically implausible -- verify data entry")
            elif self.number_of_fetuses is not None and self.number_of_fetuses >= 2:
                reasons.append(f"Multiple gestation detected ({self.number_of_fetuses} fetuses) -- higher-risk pregnancy, needs specialist referral")

        if self.scan_type == "nt_dual":
            if self.nuchal_translucency_mm is not None and self.nuchal_translucency_mm > 3.5:
                reasons.append("Increased nuchal translucency (>3.5mm)")
            if self.dual_marker_risk == "high":
                reasons.append("Dual marker screen: high risk")

        if self.scan_type == "anomaly":
            if self.fetal_movement_normal is False:
                reasons.append("Reduced/absent fetal movement on scan")

        if self.scan_type == "growth":
            if self.estimated_fetal_weight_percentile is not None and self.estimated_fetal_weight_percentile < 10:
                reasons.append("Estimated fetal weight below 10th percentile -- possible growth restriction")
            if self.estimated_fetal_weight_percentile is not None and self.estimated_fetal_weight_percentile > 90:
                reasons.append("Estimated fetal weight above 90th percentile -- possible macrosomia")

        if self.liquor_status and self.liquor_status.lower() in ("oligohydramnios", "polyhydramnios"):
            reasons.append(f"Abnormal liquor volume: {self.liquor_status}")

        self.is_flagged = bool(reasons)
        self.flag_reason = "; ".join(reasons)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_scan_type_display()} -- {self.visit}"


# ---------------------------------------------------------------------------
# 4. Visit schedule -- auto-generated expected visit dates (forward-looking)
# ---------------------------------------------------------------------------
class VisitSchedule(models.Model):
    STATUS = [("upcoming", "Upcoming"), ("completed", "Completed"), ("missed", "Missed")]

    mother = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="anc_visit_schedule",
        limit_choices_to={"role": "mother"},
    )
    expected_date = models.DateField()
    expected_gestational_week = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS, default="upcoming")
    linked_visit = models.ForeignKey(
        "hospital_portal.PrenatalVisit", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["expected_date"]

    def __str__(self):
        return f"{self.mother.username} -- expected {self.expected_date} (wk {self.expected_gestational_week})"