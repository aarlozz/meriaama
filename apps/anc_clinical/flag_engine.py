"""
anc_clinical/flag_engine.py

Pure(ish) evaluation functions -- no signal-wiring here, that's in
signals.py. Keeping this separate means you can unit-test flagging logic
directly (evaluate_visit_vitals(some_visit) -> reasons) without touching
the database or triggering signals.

FHR_MIN/FHR_MAX are here rather than in reference_data.LAB_REFERENCE_SEED
because fetal heart rate isn't a "lab test" -- it's captured directly on
PrenatalVisit, not via LabResult. If you'd rather it live in the seed
table (so clinicians can tune it from /admin like everything else), move
it there as test_code="FHR" and delete the constants below.
"""
from .reference_data import AGE_RISK_MIN, AGE_RISK_MAX, TEXT_TEST_RULES

FHR_MIN = 110   # bpm -- WHO/ACOG normal fetal heart rate band
FHR_MAX = 160
FUNDAL_HEIGHT_DISCREPANCY_CM = 3  # after wk 20, fundal height (cm) ~= gestational week +/- this


def _lookup_reference(test_code, trimester):
    """Trimester-specific row wins; falls back to the trimester=0 (Any) row."""
    from .models import LabTestReference  # lazy import, avoids circular import at app-load

    ref = LabTestReference.objects.filter(test_code=test_code, trimester=trimester).first()
    if ref is None:
        ref = LabTestReference.objects.filter(test_code=test_code, trimester=0).first()
    return ref


def evaluate_lab_result(test_code, trimester, value_numeric, value_text):
    """Returns (is_flagged: bool, severity: str, reason: str) for one LabResult."""
    code = (test_code or "").upper()

    if code in TEXT_TEST_RULES:
        rule = TEXT_TEST_RULES[code]
        text = (value_text or "").strip().lower()
        if text in rule["flag_values"]:
            return True, rule["severity"], rule["reason"]
        return False, "normal", ""

    ref = _lookup_reference(code, trimester)
    if ref is None:
        return False, "", ""
    return ref.evaluate(value_numeric)


def evaluate_visit_vitals(visit):
    """
    Returns a list of {"severity": ..., "reason": ...} dicts for one
    PrenatalVisit. Reads visit.bp_systolic/bp_diastolic, which must already
    be parsed (signals.py's pre_save handler does this before this runs).
    """
    reasons = []

    def add(severity, reason):
        reasons.append({"severity": severity, "reason": reason})

    trimester = 0
    if visit.gestational_week:
        week = visit.gestational_week
        trimester = 1 if week <= 13 else 2 if week <= 27 else 3

    # --- Blood pressure ---
    if visit.bp_systolic is not None:
        ref = _lookup_reference("BP_SYS", trimester)
        if ref:
            flagged, sev, reason = ref.evaluate(visit.bp_systolic)
            if flagged:
                add(sev, reason)
    if visit.bp_diastolic is not None:
        ref = _lookup_reference("BP_DIA", trimester)
        if ref:
            flagged, sev, reason = ref.evaluate(visit.bp_diastolic)
            if flagged:
                add(sev, reason)

    # --- Pulse / SpO2 / Hemoglobin ---
    if visit.pulse_bpm is not None:
        ref = _lookup_reference("PULSE", trimester)
        if ref:
            flagged, sev, reason = ref.evaluate(visit.pulse_bpm)
            if flagged:
                add(sev, reason)
    if visit.spo2_percent is not None:
        ref = _lookup_reference("SPO2", trimester)
        if ref:
            flagged, sev, reason = ref.evaluate(float(visit.spo2_percent))
            if flagged:
                add(sev, reason)
    if visit.hemoglobin_g_dl is not None:
        ref = _lookup_reference("HB", trimester)
        if ref:
            flagged, sev, reason = ref.evaluate(float(visit.hemoglobin_g_dl))
            if flagged:
                add(sev, reason)

    # --- Urine dipstick (categorical) ---
    if visit.urine_protein and visit.urine_protein != "negative" and visit.urine_protein != "trace":
        rule = TEXT_TEST_RULES["URINE_PROTEIN"]
        if visit.urine_protein in rule["flag_values"]:
            add(rule["severity"], rule["reason"])
    if visit.urine_glucose and visit.urine_glucose != "negative" and visit.urine_glucose != "trace":
        rule = TEXT_TEST_RULES["URINE_GLUCOSE"]
        if visit.urine_glucose in rule["flag_values"]:
            add(rule["severity"], rule["reason"])

    # --- Edema (pre-eclampsia signal, escalates if paired with high BP) ---
    if visit.edema == "severe":
        bp_high = (visit.bp_systolic and visit.bp_systolic >= 140) or (visit.bp_diastolic and visit.bp_diastolic >= 90)
        if bp_high:
            add("severe", "Severe edema with elevated BP — possible pre-eclampsia, urgent review")
        else:
            add("moderate", "Severe edema reported")
    elif visit.edema == "mild_face":
        add("moderate", "Facial edema — monitor BP and urine protein closely")

    # --- Fetal wellbeing ---
    if visit.fetal_movement == "none":
        add("severe", "No fetal movement reported — urgent assessment needed")
    elif visit.fetal_movement == "reduced":
        add("moderate", "Reduced fetal movement reported")

    if visit.fetal_heart_rate_bpm is not None:
        if visit.fetal_heart_rate_bpm < FHR_MIN:
            add("severe", f"Fetal heart rate below {FHR_MIN} bpm — fetal bradycardia")
        elif visit.fetal_heart_rate_bpm > FHR_MAX:
            add("severe", f"Fetal heart rate above {FHR_MAX} bpm — fetal tachycardia")

    # --- Fundal height vs gestational age (rough symphysio-fundal check) ---
    if visit.gestational_week and visit.gestational_week >= 20 and visit.fundal_height_cm is not None:
        discrepancy = abs(float(visit.fundal_height_cm) - visit.gestational_week)
        if discrepancy > FUNDAL_HEIGHT_DISCREPANCY_CM:
            add("moderate", f"Fundal height differs from gestational week by >{FUNDAL_HEIGHT_DISCREPANCY_CM}cm — verify dating/growth")

    # --- Exam findings ---
    if visit.lungs_abnormal:
        add("moderate", "Abnormal lung exam findings")
    if visit.heart_abnormal:
        add("moderate", "Abnormal cardiac exam findings")
    if visit.pallor_present:
        add("moderate", "Pallor present — correlate with hemoglobin")
    if visit.jaundice_present:
        add("severe", "Jaundice present — needs liver function workup")

    return reasons


def evaluate_weight_gain(visit, health_profile):
    """
    Total pregnancy weight gain check, using the fixed bands you specified
    (rather than the BMI-adjusted IOM range on HealthProfile, since staff
    need a quick yes/no flag at the bedside): flag only from week 36
    onward, since "low total gain" is meaningless mid-pregnancy.
    """
    if health_profile is None or not health_profile.pre_pregnancy_weight_kg:
        return []
    if not visit.gestational_week or visit.gestational_week < 36 or visit.maternal_weight_kg is None:
        return []
    gain = float(visit.maternal_weight_kg) - float(health_profile.pre_pregnancy_weight_kg)
    if gain < 7:
        return [{"severity": "moderate", "reason": f"Low total weight gain ({gain:.1f} kg) by term — nutritional review recommended"}]
    if gain > 18:
        return [{"severity": "moderate", "reason": f"Excessive total weight gain ({gain:.1f} kg) by term — screen for GDM/fluid retention"}]
    return []


def evaluate_maternal_age(health_profile):
    """Returns a list of {"severity", "reason"} dicts based on HealthProfile.age."""
    if health_profile is None:
        return []
    age = health_profile.age
    if age is None:
        return []
    if age < AGE_RISK_MIN:
        return [{"severity": "moderate", "reason": f"Teenage pregnancy (age {age}) — higher risk, additional monitoring recommended"}]
    if age >= AGE_RISK_MAX:
        return [{"severity": "moderate", "reason": f"Advanced maternal age ({age}) — higher risk, additional monitoring recommended"}]
    return []


def evaluate_rh_factor(health_profile):
    """Returns a list of {"severity", "reason"} dicts based on HealthProfile.blood_group."""
    if health_profile is None or not health_profile.blood_group:
        return []
    bg = health_profile.blood_group.strip()
    if bg.endswith("-"):
        return [{"severity": "moderate", "reason": f"Rh-negative ({bg}) — monitor for isoimmunization, anti-D prophylaxis at 28 weeks"}]
    return []


def evaluate_visit(visit):
    """
    Full evaluation for one PrenatalVisit: vitals + maternal age + Rh factor.
    Returns (is_flagged: bool, flag_reasons: list[dict]).
    """
    reasons = evaluate_visit_vitals(visit)
    profile = getattr(visit.mother, "health_profile", None)
    reasons += evaluate_maternal_age(profile)
    reasons += evaluate_rh_factor(profile)
    reasons += evaluate_weight_gain(visit, profile)
    return bool(reasons), reasons
