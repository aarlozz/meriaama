"""
Rule-based analysis of checkup data, grouped by trimester. This describes
PATTERNS in her own recorded data against standard antenatal reference
ranges (WHO-aligned) -- it never names a diagnosis. Every "concern"-level
flag ends with a prompt to discuss with her doctor, not a conclusion.
"""

TRIMESTER_RANGES = {1: (1, 13), 2: (14, 27), 3: (28, 999)}
MIN_EXPECTED_VISITS = {1: 1, 2: 2, 3: 4}  # rough WHO-aligned rule of thumb

FHR_NORMAL_RANGE = (110, 160)          # bpm
HEMOGLOBIN_LOW_THRESHOLD = 11.0        # g/dL, below this = possible anemia
BP_HIGH_THRESHOLD = (140, 90)          # >= this = concern
BP_ELEVATED_THRESHOLD = (130, 80)      # >= this = caution


def get_trimester(week):
    if week is None:
        return None
    if week <= 13:
        return 1
    if week <= 27:
        return 2
    return 3


def parse_bp(bp_string):
    """'120/80' -> (120, 80); returns None if unparseable."""
    try:
        systolic, diastolic = bp_string.strip().split("/")
        return int(systolic), int(diastolic)
    except (ValueError, AttributeError):
        return None


def analyze_trimester(trimester_num, visits):
    """
    visits: list of PrenatalVisit objects whose gestational_week falls in
    this trimester, already sorted oldest-first.
    Returns a dict with summary stats + a list of flags: [{severity, message}]
    severity is one of "info" (green), "caution" (amber), "concern" (red).
    """
    flags = []

    visit_count = len(visits)
    expected = MIN_EXPECTED_VISITS[trimester_num]
    if visit_count < expected:
        flags.append({
            "severity": "caution",
            "message": f"Only {visit_count} visit(s) recorded this trimester -- typically at least {expected} are recommended.",
        })

    weights = [(v.gestational_week, float(v.maternal_weight_kg)) for v in visits if v.maternal_weight_kg is not None]
    weight_change = None
    if len(weights) >= 2:
        weight_change = round(weights[-1][1] - weights[0][1], 1)
        if weight_change < 0:
            flags.append({"severity": "concern", "message": f"Weight decreased by {abs(weight_change)} kg this trimester -- worth discussing with your doctor."})
        elif weight_change > 6 and trimester_num != 1:
            flags.append({"severity": "caution", "message": f"Weight increased by {weight_change} kg this trimester -- a faster pace than typical; worth mentioning at your next visit."})

    bp_readings = [parse_bp(v.blood_pressure) for v in visits if v.blood_pressure]
    bp_readings = [r for r in bp_readings if r is not None]
    bp_flag_added = False
    for systolic, diastolic in bp_readings:
        if systolic >= BP_HIGH_THRESHOLD[0] or diastolic >= BP_HIGH_THRESHOLD[1]:
            flags.append({"severity": "concern", "message": f"A blood pressure reading of {systolic}/{diastolic} was recorded -- this is elevated and worth discussing with your doctor promptly, especially alongside any swelling or protein in urine."})
            bp_flag_added = True
            break
    if not bp_flag_added:
        for systolic, diastolic in bp_readings:
            if systolic >= BP_ELEVATED_THRESHOLD[0] or diastolic >= BP_ELEVATED_THRESHOLD[1]:
                flags.append({"severity": "caution", "message": f"A blood pressure reading of {systolic}/{diastolic} was mildly elevated -- worth keeping an eye on."})
                break

    for v in visits:
        if v.fundal_height_cm is not None and v.gestational_week and 20 <= v.gestational_week <= 36:
            deviation = abs(float(v.fundal_height_cm) - v.gestational_week)
            if deviation > 3:
                flags.append({"severity": "caution", "message": f"Fundal height ({v.fundal_height_cm} cm) at week {v.gestational_week} differs from the typical range -- your doctor may want to follow up."})
                break

    for v in visits:
        if v.fetal_heart_rate_bpm is not None:
            if not (FHR_NORMAL_RANGE[0] <= v.fetal_heart_rate_bpm <= FHR_NORMAL_RANGE[1]):
                flags.append({"severity": "concern", "message": f"A fetal heart rate of {v.fetal_heart_rate_bpm} bpm was recorded, outside the typical 110-160 bpm range -- discuss with your doctor."})
                break

    for v in visits:
        if v.fetal_movement in ("reduced", "none") and trimester_num >= 2:
            flags.append({"severity": "concern", "message": "Reduced or absent fetal movement was reported -- if this is recent or ongoing, contact your doctor promptly."})
            break

    protein_positive = any(v.urine_protein in ("plus1", "plus2", "plus3") for v in visits)
    glucose_positive = any(v.urine_glucose in ("plus1", "plus2", "plus3") for v in visits)
    if protein_positive:
        flags.append({"severity": "concern", "message": "Protein was detected in urine at least once this trimester -- this can be an early sign worth discussing with your doctor."})
    if glucose_positive:
        flags.append({"severity": "caution", "message": "Glucose was detected in urine at least once this trimester -- your doctor may want to screen for gestational diabetes if not already done."})

    low_hemoglobin = [v for v in visits if v.hemoglobin_g_dl is not None and float(v.hemoglobin_g_dl) < HEMOGLOBIN_LOW_THRESHOLD]
    if low_hemoglobin:
        flags.append({"severity": "caution", "message": f"Hemoglobin of {low_hemoglobin[0].hemoglobin_g_dl} g/dL was recorded, below the typical pregnancy threshold -- may indicate anemia, worth discussing with your doctor."})

    if trimester_num == 3:
        for v in visits:
            if v.fetal_position in ("breech", "transverse") and v.gestational_week and v.gestational_week >= 34:
                flags.append({"severity": "caution", "message": f"Fetal position was recorded as {v.get_fetal_position_display()} at week {v.gestational_week} -- your doctor will likely discuss delivery planning options."})
                break

    severe_edema = any(v.edema == "severe" for v in visits)
    any_edema = any(v.edema and v.edema != "none" for v in visits)
    if severe_edema:
        flags.append({"severity": "concern", "message": "Severe swelling was recorded -- please discuss this with your doctor."})

    if bp_flag_added and protein_positive and any_edema:
        flags.append({
            "severity": "concern",
            "message": "Elevated blood pressure, protein in urine, and swelling were all recorded this trimester -- this combination is worth raising with your doctor as soon as possible.",
        })

    return {
        "trimester_num": trimester_num,
        "visit_count": visit_count,
        "weight_start": weights[0][1] if weights else None,
        "weight_end": weights[-1][1] if weights else None,
        "weight_change": weight_change,
        "flags": flags,
    }


def build_full_analysis(all_visits):
    """Groups visits into trimester 1/2/3 buckets and analyzes each."""
    buckets = {1: [], 2: [], 3: []}
    for v in all_visits:
        t = get_trimester(v.gestational_week)
        if t:
            buckets[t].append(v)

    for t in buckets:
        buckets[t].sort(key=lambda v: v.gestational_week or 0)

    return [analyze_trimester(t, buckets[t]) for t in (1, 2, 3)]