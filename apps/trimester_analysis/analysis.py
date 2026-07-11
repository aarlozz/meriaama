"""
Trimester Analysis Engine
-------------------------

Responsibilities
----------------
- Pregnancy progress (current week, completion %, milestones)
- Trimester summaries (weight, BP, hemoglobin, FHR, urine, edema)
- Clinical alerts (flags), grouped and overall
- Timeline + chart data generation
- AI narrative prompt generation

The AI model never analyses raw visit objects. Python performs all clinical
calculations first, then only structured facts are sent to the LLM, and the
LLM is instructed to respond in structured JSON, not free text.
"""

from collections import defaultdict
from statistics import mean

from apps.hospital_portal.models import TRACKED_FIELDS

# ---------------------------------------------------------
# Clinical Thresholds
# ---------------------------------------------------------

TRIMESTER_RANGES = {
    1: (1, 13),
    2: (14, 27),
    3: (28, 45),
}

NORMAL_FHR = (110, 160)
NORMAL_HB = 11.0
NORMAL_BP = (120, 80)
ELEVATED_BP = (130, 80)
HIGH_BP = (140, 90)
SEVERE_BP = (160, 110)

FHR_NORMAL_RANGE = (110, 160)
HEMOGLOBIN_LOW_THRESHOLD = 11.0
BP_HIGH_THRESHOLD = (140, 90)
BP_ELEVATED_THRESHOLD = (130, 80)

# ---------------------------------------------------------
# Basic Helpers
# ---------------------------------------------------------


def get_trimester(week):
    """Convert gestational week into trimester number."""
    if week is None:
        return None
    if week <= 13:
        return 1
    if week <= 27:
        return 2
    return 3


def trimester_name(number):
    return {
        1: "First Trimester",
        2: "Second Trimester",
        3: "Third Trimester",
    }.get(number, "Unknown")


# ---------------------------------------------------------
# Blood Pressure Parser
# ---------------------------------------------------------


def parse_bp(bp):
    """Converts '120/80' into (120, 80)."""
    if not bp:
        return None
    try:
        systolic, diastolic = bp.split("/")
        return int(systolic), int(diastolic)
    except Exception:
        return None


# ---------------------------------------------------------
# Trend Helpers
# ---------------------------------------------------------


def calculate_change(current, previous):
    if current is None or previous is None:
        return None
    diff = round(float(current) - float(previous), 1)
    if diff > 0:
        direction = "up"
    elif diff < 0:
        direction = "down"
    else:
        direction = "same"
    return {"difference": diff, "direction": direction}


def trend_direction(values):
    """Returns 'Increasing', 'Stable', 'Decreasing', or 'Insufficient Data'."""
    values = [float(v) for v in values if v is not None]
    if len(values) < 2:
        return "Insufficient Data"
    diff = values[-1] - values[0]
    if abs(diff) < 0.5:
        return "Stable"
    return "Increasing" if diff > 0 else "Decreasing"


# ---------------------------------------------------------
# Safe Statistics
# ---------------------------------------------------------


def average(values):
    values = [float(v) for v in values if v is not None]
    if not values:
        return None
    return round(mean(values), 1)


def latest(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return values[-1]


def first(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return values[0]


# ---------------------------------------------------------
# Health Status Helpers
# ---------------------------------------------------------


def bp_status(bp):
    bp = parse_bp(bp)
    if not bp:
        return "Unknown"
    s, d = bp
    if s >= SEVERE_BP[0] or d >= SEVERE_BP[1]:
        return "Severely High"
    if s >= HIGH_BP[0] or d >= HIGH_BP[1]:
        return "High"
    if s >= ELEVATED_BP[0] or d >= ELEVATED_BP[1]:
        return "Elevated"
    return "Normal"


def hb_status(hb):
    if hb is None:
        return "Unknown"
    if float(hb) < 7:
        return "Critical"
    if float(hb) < NORMAL_HB:
        return "Low"
    return "Normal"


def fhr_status(rate):
    if rate is None:
        return "Unknown"
    if rate < NORMAL_FHR[0]:
        return "Low"
    if rate > NORMAL_FHR[1]:
        return "High"
    return "Normal"


# ---------------------------------------------------------
# Chart + Timeline Builders
# ---------------------------------------------------------


def build_chart_data(visits):
    charts = {"weeks": [], "weight": [], "hb": [], "fundal": [], "fhr": [], "bp_sys": [], "bp_dia": []}

    for visit in visits:
        if visit.gestational_week is None:
            continue

        charts["weeks"].append(visit.gestational_week)
        charts["weight"].append(float(visit.maternal_weight_kg) if visit.maternal_weight_kg is not None else None)
        charts["hb"].append(float(visit.hemoglobin_g_dl) if visit.hemoglobin_g_dl is not None else None)
        charts["fundal"].append(float(visit.fundal_height_cm) if visit.fundal_height_cm is not None else None)
        charts["fhr"].append(visit.fetal_heart_rate_bpm)

        bp = parse_bp(visit.blood_pressure)
        if bp:
            charts["bp_sys"].append(bp[0])
            charts["bp_dia"].append(bp[1])
        else:
            charts["bp_sys"].append(None)
            charts["bp_dia"].append(None)

    return charts


def build_timeline(visits):
    visits = sorted(visits, key=lambda x: (x.gestational_week or 0, x.visit_date))
    timeline = []
    previous = None

    for visit in visits:
        item = {
            "visit": visit,
            "week": visit.gestational_week,
            "date": visit.visit_date,
            "trimester": get_trimester(visit.gestational_week),
            "changes": {},
        }

        if previous:
            item["changes"]["weight"] = calculate_change(visit.maternal_weight_kg, previous.maternal_weight_kg)
            item["changes"]["fundal_height"] = calculate_change(visit.fundal_height_cm, previous.fundal_height_cm)
            item["changes"]["hemoglobin"] = calculate_change(visit.hemoglobin_g_dl, previous.hemoglobin_g_dl)
            item["changes"]["fhr"] = calculate_change(visit.fetal_heart_rate_bpm, previous.fetal_heart_rate_bpm)

        timeline.append(item)
        previous = visit

    return timeline


# ---------------------------------------------------------
# Per-Trimester Analysis
# ---------------------------------------------------------


def analyze_trimester(trimester, visits, profile=None):
    """Performs detailed analysis for one trimester."""
    visits = sorted(visits, key=lambda x: (x.gestational_week or 0, x.visit_date))

    result = {
        "trimester": trimester,
        "title": f"Trimester {trimester}",
        "visit_count": len(visits),
        "status": "good",
        "summary": "",
        "highlights": [],
        "concerns": [],
        "recommendations": [],
        "weight_start": None,
        "weight_end": None,
        "weight_gain": None,
        "charts": build_chart_data(visits),
        "timeline": build_timeline(visits),
    }

    if not visits:
        result["status"] = "no_data"
        result["summary"] = "No prenatal visits recorded."
        result["flags"] = []
        return result

    # -------------------------------------------------------
    # Weight Analysis
    # -------------------------------------------------------
    weights = [float(v.maternal_weight_kg) for v in visits if v.maternal_weight_kg is not None]

    result["weight_start"] = weights[0] if weights else None
    result["weight_end"] = weights[-1] if weights else None

    if len(weights) >= 2:
        gain = round(weights[-1] - weights[0], 1)
        result["weight_gain"] = gain
        result["highlights"].append({"title": "Weight change", "value": f"{gain:+.1f} kg"})
        if gain < 0:
            result["concerns"].append("Weight has decreased during this trimester.")
    elif weights:
        result["highlights"].append({"title": "Current weight", "value": f"{weights[-1]} kg"})

    # -------------------------------------------------------
    # Blood Pressure
    # -------------------------------------------------------
    bp_values = []
    for visit in visits:
        bp = parse_bp(visit.blood_pressure)
        if not bp:
            continue
        bp_values.append(bp)

        if bp[0] >= BP_HIGH_THRESHOLD[0] or bp[1] >= BP_HIGH_THRESHOLD[1]:
            result["status"] = "attention"
            result["concerns"].append(f"Week {visit.gestational_week}: Blood pressure reached {bp[0]}/{bp[1]}.")
        elif bp[0] >= BP_ELEVATED_THRESHOLD[0] or bp[1] >= BP_ELEVATED_THRESHOLD[1]:
            result["concerns"].append(f"Week {visit.gestational_week}: Mild blood pressure elevation.")

    if bp_values:
        avg_sys = round(sum(i[0] for i in bp_values) / len(bp_values))
        avg_dia = round(sum(i[1] for i in bp_values) / len(bp_values))
        result["highlights"].append({"title": "Average BP", "value": f"{avg_sys}/{avg_dia}"})

    # -------------------------------------------------------
    # Hemoglobin
    # -------------------------------------------------------
    hb = [float(v.hemoglobin_g_dl) for v in visits if v.hemoglobin_g_dl is not None]
    if hb:
        latest_hb = hb[-1]
        result["highlights"].append({"title": "Hemoglobin", "value": f"{latest_hb:.1f} g/dL"})
        if latest_hb < HEMOGLOBIN_LOW_THRESHOLD:
            result["concerns"].append("Latest hemoglobin is below the recommended level.")

    # -------------------------------------------------------
    # Fetal Heart Rate
    # -------------------------------------------------------
    fhr = [v.fetal_heart_rate_bpm for v in visits if v.fetal_heart_rate_bpm]
    if fhr:
        latest_fhr = fhr[-1]
        result["highlights"].append({"title": "Latest fetal heart rate", "value": f"{latest_fhr} bpm"})
        if not (FHR_NORMAL_RANGE[0] <= latest_fhr <= FHR_NORMAL_RANGE[1]):
            result["concerns"].append("Latest fetal heart rate is outside the usual range.")

    # -------------------------------------------------------
    # Urine Protein
    # -------------------------------------------------------
    protein_positive = any(v.urine_protein in ("plus1", "plus2", "plus3") for v in visits)
    if protein_positive:
        result["concerns"].append("Protein was detected in urine during this trimester.")

    # -------------------------------------------------------
    # Edema
    # -------------------------------------------------------
    edema = any(v.edema in ("mild_face", "mild_hands_feet", "severe") for v in visits)
    if edema:
        result["concerns"].append("Swelling was recorded during this trimester.")

    # -------------------------------------------------------
    # Summary + Recommendations
    # -------------------------------------------------------
    if not result["concerns"]:
        result["summary"] = "Measurements remained generally stable throughout this trimester."
    else:
        result["summary"] = f"{len(result['concerns'])} observation(s) may require discussion during your next antenatal visit."
        result["recommendations"].append("Continue attending scheduled prenatal visits.")
        result["recommendations"].append("Discuss any persistent symptoms with your healthcare provider.")

    # Flags -- used by the template's "Clinical Findings" section
    result["flags"] = [{"severity": "concern", "message": c} for c in result["concerns"]]

    return result


# ---------------------------------------------------------
# Overall Summary
# ---------------------------------------------------------


def calculate_health_score(results):
    """Starts at 100 and subtracts points for abnormal findings."""
    score = 100
    for trimester in results:
        for concern in trimester["concerns"]:
            text = concern.lower()
            if "blood pressure" in text:
                score -= 10
            elif "hemoglobin" in text:
                score -= 8
            elif "protein" in text:
                score -= 10
            elif "heart rate" in text:
                score -= 10
            elif "swelling" in text:
                score -= 5
            else:
                score -= 3
    return max(score, 0)


def determine_risk(score):
    if score >= 90:
        return {"label": "Low Risk", "color": "green"}
    if score >= 70:
        return {"label": "Moderate Risk", "color": "yellow"}
    return {"label": "Needs Attention", "color": "red"}


def build_overall_summary(results):
    total_visits = sum(r["visit_count"] for r in results)
    concerns, highlights = [], []

    for trimester in results:
        concerns.extend(trimester["concerns"])
        highlights.extend(trimester["highlights"])

    score = calculate_health_score(results)
    risk = determine_risk(score)

    return {
        "health_score": score,
        "risk": risk,
        "total_visits": total_visits,
        "total_concerns": len(concerns),
        "highlights": highlights,
        "concerns": concerns,
    }


# ---------------------------------------------------------
# Progress / Milestones
# ---------------------------------------------------------


def calculate_completion(visits):
    """Calculates how complete the clinical records are, across the tracked fields."""
    if not visits:
        return 0

    total = len(TRACKED_FIELDS) * len(visits)
    completed = 0

    for visit in visits:
        for field_name, _ in TRACKED_FIELDS:
            value = getattr(visit, field_name)
            if value not in (None, ""):
                completed += 1

    return round(completed / total * 100)


def build_milestones(profile, latest_visit):
    milestones = []
    if not latest_visit:
        return milestones

    week = latest_visit.gestational_week or 0

    if week >= 12:
        milestones.append("First trimester completed.")
    if week >= 20:
        milestones.append("Halfway through pregnancy.")
    if week >= 28:
        milestones.append("Third trimester started.")
    if week >= 37:
        milestones.append("Early-term pregnancy reached.")

    if profile and profile.expected_delivery_date:
        milestones.append(f"Expected delivery: {profile.expected_delivery_date}")

    return milestones


def build_progress(profile, visits):
    latest_visit = visits[-1] if visits else None

    return {
        "completion": calculate_completion(visits),
        "milestones": build_milestones(profile, latest_visit),
        "current_week": getattr(latest_visit, "gestational_week", None),
        "latest_visit": latest_visit,
    }


# ---------------------------------------------------------
# Full Analysis Entry Point
# ---------------------------------------------------------


def build_full_analysis(all_visits, profile=None):
    buckets = defaultdict(list)

    for visit in all_visits:
        trimester = get_trimester(visit.gestational_week)
        if trimester:
            buckets[trimester].append(visit)

    trimester_results = [analyze_trimester(t, buckets[t], profile) for t in (1, 2, 3)]

    overall = build_overall_summary(trimester_results)
    charts = build_chart_data(all_visits)
    timeline = build_timeline(all_visits)
    progress = build_progress(profile, all_visits)

    return {
        "overall": overall,
        "progress": progress,
        "trimesters": trimester_results,
        "timeline": timeline,
        "charts": charts,
    }


# ---------------------------------------------------------
# AI Narrative Prompt
# ---------------------------------------------------------


def generate_narrative_prompt(trimesters):
    """
    Builds the (system_prompt, user_prompt) pair sent to Groq. Only ever
    receives already-computed structured facts (highlights/concerns per
    trimester) -- never raw visit objects. Instructs the model to respond
    as structured JSON so the template can render it properly, instead of
    a single opaque paragraph.
    """
    lines = []
    for t in trimesters:
        lines.append(f"{t['title']} -- {t['visit_count']} visit(s)")
        if t.get("weight_gain") is not None:
            lines.append(f"  Weight change: {t['weight_gain']:+.1f} kg")
        for item in t["highlights"]:
            lines.append(f"  Highlight: {item['title']} = {item['value']}")
        for concern in t["concerns"]:
            lines.append(f"  Concern: {concern}")
        lines.append("")

    system_prompt = (
        "You are a compassionate maternal health assistant. Summarize ONLY "
        "the supplied facts below -- do not invent or infer anything not "
        "explicitly present. Respond ONLY as JSON in this exact shape:\n"
        '{"overall_progress": "1-2 sentence overview", '
        '"trimester_notes": [{"trimester": 1, "note": "..."}, ...], '
        '"positive_signs": ["...", ...], '
        '"things_to_discuss": ["...", ...], '
        '"next_visit_advice": "1-2 sentences"}\n'
        "Never diagnose. Never invent facts. Never recommend medications. "
        "Use a warm, reassuring tone. If a trimester has no visits, its note "
        "should simply say so."
    )
    return system_prompt, "\n".join(lines)