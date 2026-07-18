"""
Trimester Analysis Engine
-------------------------

Responsibilities
----------------
- Pregnancy progress (current week, completion %, milestones)
- Trimester summaries built from ALL recorded clinical data: vitals,
  lab results, and ultrasound reports -- not just the 10 core visit
  fields.
- Severity is NEVER re-derived here. This app used to duplicate its own
  crude BP/Hb thresholds and guess severity from keyword-matching on
  concern strings, which drifted from the real clinical rules in
  anc_clinical. Now:
    * vitals severity  -> PrenatalVisit.flag_reasons (anc_clinical.flag_engine)
    * lab severity      -> LabResult.severity (anc_clinical.models / LabTestReference)
    * scan severity     -> classified locally (UltrasoundReport has no
                            severity field yet, just is_flagged/flag_reason)
  This keeps trimester_analysis and the pregnancy dashboard from ever
  disagreeing about whether something is "moderate" or "severe".
- Per-trimester "what's missing" list, reusing
  anc_clinical.schedule_rules.trimester_checklist so pending labs/scans
  match what the dashboard already shows.
- Timeline + chart data generation (now includes labs/scans per visit)
- AI narrative prompt generation

The AI model never analyses raw visit objects. Python performs all clinical
calculations first, then only structured facts are sent to the LLM, and the
LLM is instructed to respond in structured JSON, not free text.
"""

from collections import defaultdict
from statistics import mean

from apps.hospital_portal.models import TRACKED_FIELDS

# ---------------------------------------------------------
# Display-only thresholds (BP/HB "status" labels for charts/highlights).
# NOT used to decide severity or flagging anymore -- that's owned by
# anc_clinical.flag_engine / LabResult.severity / LabTestReference.
# ---------------------------------------------------------

TRIMESTER_RANGES = {1: (1, 13), 2: (14, 27), 3: (28, 45)}

NORMAL_FHR = (110, 160)
NORMAL_HB = 11.0
ELEVATED_BP = (130, 80)
HIGH_BP = (140, 90)
SEVERE_BP = (160, 110)

FHR_NORMAL_RANGE = (110, 160)

# UltrasoundReport doesn't carry a severity field, so classify from the
# reason text it already writes in UltrasoundReport.clean(). Keep this in
# sync if the wording there ever changes.
ULTRASOUND_SEVERE_MARKERS = (
    "not confirmed",
    "no fetal cardiac activity",
    "implausible",
    "below 10th percentile",
)


def ultrasound_severity(report):
    """Classify an already-flagged UltrasoundReport as moderate/severe."""
    if not report.is_flagged:
        return None
    text = (report.flag_reason or "").lower()
    if any(marker in text for marker in ULTRASOUND_SEVERE_MARKERS):
        return "severe"
    return "moderate"


# ---------------------------------------------------------
# Basic Helpers
# ---------------------------------------------------------


def get_trimester(week):
    if week is None:
        return None
    if week <= 13:
        return 1
    if week <= 27:
        return 2
    return 3


def trimester_name(number):
    return {1: "First Trimester", 2: "Second Trimester", 3: "Third Trimester"}.get(number, "Unknown")


def parse_bp(bp):
    """Converts '120/80' into (120, 80)."""
    if not bp:
        return None
    try:
        systolic, diastolic = bp.split("/")
        return int(systolic), int(diastolic)
    except Exception:
        return None


def calculate_change(current, previous):
    if current is None or previous is None:
        return None
    diff = round(float(current) - float(previous), 1)
    direction = "up" if diff > 0 else "down" if diff < 0 else "same"
    return {"difference": diff, "direction": direction}


def trend_direction(values):
    values = [float(v) for v in values if v is not None]
    if len(values) < 2:
        return "Insufficient Data"
    diff = values[-1] - values[0]
    if abs(diff) < 0.5:
        return "Stable"
    return "Increasing" if diff > 0 else "Decreasing"


def average(values):
    values = [float(v) for v in values if v is not None]
    return round(mean(values), 1) if values else None


def latest(values):
    values = [v for v in values if v is not None]
    return values[-1] if values else None


def first(values):
    values = [v for v in values if v is not None]
    return values[0] if values else None


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
# Flag builders -- these READ existing severity, they don't compute it
# ---------------------------------------------------------


def _visit_flags(visits):
    flags = []
    for v in visits:
        for reason in (v.flag_reasons or []):
            flags.append({
                "date": v.visit_date,
                "week": v.gestational_week,
                "source": "Vitals",
                "severity": reason.get("severity", "moderate"),
                "message": reason.get("reason", ""),
            })
    return flags


def _lab_flags(labs):
    flags = []
    for lr in labs:
        if not lr.is_flagged:
            continue
        flags.append({
            "date": lr.recorded_at.date() if lr.recorded_at else None,
            "week": getattr(lr.visit, "gestational_week", None),
            "source": "Lab",
            "severity": lr.severity or "moderate",
            "message": f"{lr.test_name}: {lr.flag_reason}" if lr.flag_reason else f"{lr.test_name} flagged",
        })
    return flags


def _scan_flags(scans):
    flags = []
    for ur in scans:
        if not ur.is_flagged:
            continue
        flags.append({
            "date": ur.scan_date,
            "week": getattr(ur.visit, "gestational_week", None),
            "source": "Ultrasound",
            "severity": ultrasound_severity(ur) or "moderate",
            "message": f"{ur.get_scan_type_display()}: {ur.flag_reason}" if ur.flag_reason else ur.get_scan_type_display(),
        })
    return flags


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


def build_timeline(visits, labs=None, scans=None):
    """
    One entry per visit, now carrying that visit's own lab results,
    ultrasound reports, and clinical flags -- not just the 10 core
    vitals fields.
    """
    labs_by_visit = defaultdict(list)
    for lr in (labs or []):
        labs_by_visit[lr.visit_id].append(lr)

    scans_by_visit = defaultdict(list)
    for ur in (scans or []):
        scans_by_visit[ur.visit_id].append(ur)

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
            "labs": labs_by_visit.get(visit.id, []),
            "scans": scans_by_visit.get(visit.id, []),
            "flags": visit.flag_reasons or [],
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


def analyze_trimester(trimester, visits, profile=None, checklist=None, labs=None, scans=None):
    """
    Performs detailed analysis for one trimester using vitals + labs +
    scans together, with severity taken from the already-computed
    anc_clinical values (never re-derived here).
    """
    visits = sorted(visits, key=lambda x: (x.gestational_week or 0, x.visit_date))
    labs = labs or []
    scans = scans or []

    result = {
        "trimester": trimester,
        "title": f"Trimester {trimester}",
        "visit_count": len(visits),
        "status": "good",
        "summary": "",
        "highlights": [],
        "flags": [],
        "severe_count": 0,
        "moderate_count": 0,
        "recommendations": [],
        "weight_start": None,
        "weight_end": None,
        "weight_gain": None,
        "charts": build_chart_data(visits),
        "timeline": build_timeline(visits, labs, scans),
        "checklist": checklist,  # {"labs": [...], "scans": [...]} or None
    }

    if not visits:
        result["status"] = "no_data"
        result["summary"] = "No prenatal visits recorded."
        if checklist:
            missing_labs = [l["label"] for l in checklist["labs"] if not l["recorded"]]
            missing_scans = [s["label"] for s in checklist["scans"] if not s["recorded"]]
            if missing_labs:
                result["recommendations"].append(f"Not yet recorded: {', '.join(missing_labs)}.")
            if missing_scans:
                result["recommendations"].append(f"Scan(s) not yet done: {', '.join(missing_scans)}.")
        return result

    # -------------------------------------------------------
    # Weight
    # -------------------------------------------------------
    weights = [float(v.maternal_weight_kg) for v in visits if v.maternal_weight_kg is not None]
    result["weight_start"] = weights[0] if weights else None
    result["weight_end"] = weights[-1] if weights else None
    if len(weights) >= 2:
        gain = round(weights[-1] - weights[0], 1)
        result["weight_gain"] = gain
        result["highlights"].append({"title": "Weight change", "value": f"{gain:+.1f} kg"})
    elif weights:
        result["highlights"].append({"title": "Current weight", "value": f"{weights[-1]} kg"})

    # -------------------------------------------------------
    # Display-only highlights (BP / Hb / FHR) -- severity comes from flags below
    # -------------------------------------------------------
    bp_values = [parse_bp(v.blood_pressure) for v in visits if parse_bp(v.blood_pressure)]
    if bp_values:
        avg_sys = round(sum(b[0] for b in bp_values) / len(bp_values))
        avg_dia = round(sum(b[1] for b in bp_values) / len(bp_values))
        result["highlights"].append({"title": "Average BP", "value": f"{avg_sys}/{avg_dia}"})

    hb_values = [float(v.hemoglobin_g_dl) for v in visits if v.hemoglobin_g_dl is not None]
    if hb_values:
        result["highlights"].append({"title": "Hemoglobin", "value": f"{hb_values[-1]:.1f} g/dL"})

    fhr_values = [v.fetal_heart_rate_bpm for v in visits if v.fetal_heart_rate_bpm]
    if fhr_values:
        result["highlights"].append({"title": "Latest fetal heart rate", "value": f"{fhr_values[-1]} bpm"})

    if labs:
        result["highlights"].append({"title": "Lab results this trimester", "value": str(len(labs))})
    if scans:
        result["highlights"].append({"title": "Scans this trimester", "value": str(len(scans))})

    # -------------------------------------------------------
    # Real clinical flags -- vitals + labs + scans, merged and sorted
    # -------------------------------------------------------
    flags = _visit_flags(visits) + _lab_flags(labs) + _scan_flags(scans)
    flags.sort(key=lambda f: f["date"] or visits[0].visit_date)
    result["flags"] = flags

    severe = [f for f in flags if f["severity"] == "severe"]
    moderate = [f for f in flags if f["severity"] == "moderate"]
    result["severe_count"] = len(severe)
    result["moderate_count"] = len(moderate)
    result["status"] = "attention" if severe else ("monitor" if moderate else "good")

    # -------------------------------------------------------
    # What's missing this trimester -- reused from anc_clinical so this
    # never disagrees with the pregnancy dashboard's own checklist
    # -------------------------------------------------------
    if checklist:
        missing_labs = [l["label"] for l in checklist["labs"] if not l["recorded"]]
        missing_scans = [s["label"] for s in checklist["scans"] if not s["recorded"]]
        if missing_labs:
            result["recommendations"].append(f"Still pending this trimester: {', '.join(missing_labs)}.")
        if missing_scans:
            result["recommendations"].append(f"Scan(s) not yet done: {', '.join(missing_scans)}.")

    if severe:
        result["recommendations"].append("Discuss the severe finding(s) below with your doctor as soon as possible.")
    elif moderate:
        result["recommendations"].append("Bring up the flagged item(s) below at your next visit.")

    # -------------------------------------------------------
    # Summary
    # -------------------------------------------------------
    if not flags:
        result["summary"] = "Measurements remained generally stable throughout this trimester."
    elif severe:
        result["summary"] = f"{len(severe)} finding(s) need prompt attention, plus {len(moderate)} to monitor."
    else:
        result["summary"] = f"{len(moderate)} observation(s) may require discussion during your next antenatal visit."

    return result


# ---------------------------------------------------------
# Overall Summary
# ---------------------------------------------------------


def calculate_health_score(results):
    """Starts at 100, subtracts by REAL severity counts (not keyword guesses)."""
    score = 100
    for t in results:
        score -= t.get("severe_count", 0) * 12
        score -= t.get("moderate_count", 0) * 5
    return max(score, 0)


def determine_risk(score):
    if score >= 90:
        return {"label": "Low Risk", "color": "green"}
    if score >= 70:
        return {"label": "Moderate Risk", "color": "yellow"}
    return {"label": "Needs Attention", "color": "red"}


def build_overall_summary(results):
    total_visits = sum(r["visit_count"] for r in results)
    flags, highlights, recommendations = [], [], []

    for t in results:
        flags.extend(t.get("flags", []))
        highlights.extend(t["highlights"])
        recommendations.extend(t.get("recommendations", []))

    score = calculate_health_score(results)
    risk = determine_risk(score)

    return {
        "health_score": score,
        "risk": risk,
        "total_visits": total_visits,
        "total_concerns": len(flags),
        "severe_count": sum(t.get("severe_count", 0) for t in results),
        "moderate_count": sum(t.get("moderate_count", 0) for t in results),
        "highlights": highlights,
        "flags": flags,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------
# Progress / Milestones
# ---------------------------------------------------------


def calculate_completion(visits):
    if not visits:
        return 0
    total = len(TRACKED_FIELDS) * len(visits)
    completed = 0
    for visit in visits:
        for field_name, _ in TRACKED_FIELDS:
            if getattr(visit, field_name) not in (None, ""):
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


def build_full_analysis(all_visits, profile=None, mother=None):
    """
    mother is required to pull labs/scans and the anc_clinical checklist.
    Falls back gracefully (no lab/scan data, no checklist) if not passed,
    so this doesn't hard-break other callers.
    """
    from apps.anc_clinical.models import LabResult, UltrasoundReport

    visit_ids = [v.id for v in all_visits]
    all_labs = list(LabResult.objects.filter(visit_id__in=visit_ids).select_related("visit")) if visit_ids else []
    all_scans = list(UltrasoundReport.objects.filter(visit_id__in=visit_ids).select_related("visit")) if visit_ids else []

    buckets = defaultdict(list)
    for visit in all_visits:
        trimester = get_trimester(visit.gestational_week)
        if trimester:
            buckets[trimester].append(visit)

    checklists = {}
    if mother is not None:
        from apps.anc_clinical.schedule_rules import trimester_checklist as _trimester_checklist
        latest_week = all_visits[-1].gestational_week if all_visits else None
        for entry in _trimester_checklist(mother, latest_week):
            checklists[entry["number"]] = entry

    trimester_results = []
    for t in (1, 2, 3):
        t_visits = buckets[t]
        t_ids = {v.id for v in t_visits}
        t_labs = [lr for lr in all_labs if lr.visit_id in t_ids]
        t_scans = [ur for ur in all_scans if ur.visit_id in t_ids]
        trimester_results.append(
            analyze_trimester(t, t_visits, profile, checklist=checklists.get(t), labs=t_labs, scans=t_scans)
        )

    overall = build_overall_summary(trimester_results)
    charts = build_chart_data(all_visits)
    timeline = build_timeline(all_visits, all_labs, all_scans)
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
    receives already-computed structured facts -- never raw visit/lab/scan
    objects. Instructs the model to respond as structured JSON.
    """
    lines = []
    for t in trimesters:
        lines.append(f"{t['title']} -- {t['visit_count']} visit(s)")
        if t.get("weight_gain") is not None:
            lines.append(f"  Weight change: {t['weight_gain']:+.1f} kg")
        for item in t["highlights"]:
            lines.append(f"  Highlight: {item['title']} = {item['value']}")
        for flag in t.get("flags", []):
            lines.append(f"  {flag['severity'].capitalize()} ({flag['source']}): {flag['message']}")
        for rec in t.get("recommendations", []):
            lines.append(f"  Pending/recommended: {rec}")
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