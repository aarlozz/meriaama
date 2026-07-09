"""
Pregnancy Dashboard services: risk scoring + AI summary.

IMPORTANT: `calculate_risk` is a transparent, rule-based flagging tool using
standard antenatal red-flag ranges (BP, hemoglobin, fetal heart rate, edema,
urine protein). It is NOT a diagnostic tool and does not replace clinical
judgement -- it exists to surface "worth mentioning at your next visit"
items to the mother, same spirit as the rest of the app's non-diagnostic
framing (see psychometric app). Keep the thresholds and reasons visible/
explainable; don't turn this into an opaque score.
"""
import json

from django.conf import settings


# Reuse your existing Groq client setup if you already have one shared
# across daily_wellness / pdf_insight (e.g. apps/common/groq_client.py) --
# swap this import for that. Shown standalone here for clarity.
from groq import Groq

client = Groq(api_key=settings.GROQ_API_KEY)

GROQ_MODEL = "openai/gpt-oss-120b"


def _latest_value(visits, field_name):
    """First non-null/non-blank value for `field_name`, newest visit first."""
    for v in visits:
        val = getattr(v, field_name)
        if val not in (None, ""):
            return val
    return None


def calculate_risk(mother):
    """
    Looks at the most recent recorded value for each relevant field (not
    necessarily all from the same visit, since not every field is filled
    at every checkup) and flags anything outside typical ranges.

    Returns: {"level": "low" | "moderate" | "high", "reasons": [str, ...]}
    """
    from apps.hospital_portal.models import PrenatalVisit # local import to avoid circularity

    visits = list(mother.prenatal_visits.all())  # Meta.ordering = -visit_date
    reasons = []
    high = False
    moderate = False

    bp = _latest_value(visits, "blood_pressure")
    edema = _latest_value(visits, "edema")
    urine_protein = _latest_value(visits, "urine_protein")
    hb = _latest_value(visits, "hemoglobin_g_dl")
    fhr = _latest_value(visits, "fetal_heart_rate_bpm")
    fetal_movement = _latest_value(visits, "fetal_movement")

    if bp:
        try:
            sys_bp, dia_bp = (int(x) for x in bp.split("/"))
            if sys_bp >= 140 or dia_bp >= 90:
                high = True
                reasons.append(f"Blood pressure elevated ({bp})")
            elif sys_bp >= 130 or dia_bp >= 85:
                moderate = True
                reasons.append(f"Blood pressure slightly elevated ({bp})")
        except (ValueError, AttributeError):
            pass

    if edema == PrenatalVisit.Edema.SEVERE:
        high = True
        reasons.append("Severe swelling reported")
    elif edema == PrenatalVisit.Edema.MILD_FACE:
        moderate = True
        reasons.append("Mild facial swelling reported")

    if urine_protein in (PrenatalVisit.UrineLevel.PLUS2, PrenatalVisit.UrineLevel.PLUS3):
        high = True
        reasons.append("Protein detected in urine")
    elif urine_protein in (PrenatalVisit.UrineLevel.TRACE, PrenatalVisit.UrineLevel.PLUS1):
        moderate = True
        reasons.append("Trace protein detected in urine")

    if hb is not None:
        hb_val = float(hb)
        if hb_val < 9:
            high = True
            reasons.append(f"Hemoglobin low ({hb_val} g/dL)")
        elif hb_val < 11:
            moderate = True
            reasons.append(f"Hemoglobin slightly low ({hb_val} g/dL)")

    if fhr is not None and (fhr < 110 or fhr > 160):
        high = True
        reasons.append(f"Fetal heart rate outside typical range ({fhr} bpm)")

    if fetal_movement == PrenatalVisit.FetalMovement.NONE:
        high = True
        reasons.append("No fetal movement reported")
    elif fetal_movement == PrenatalVisit.FetalMovement.REDUCED:
        moderate = True
        reasons.append("Reduced fetal movement reported")

    level = "high" if high else ("moderate" if moderate else "low")
    if not reasons:
        reasons = ["No concerning values recorded in the latest checkup data."]

    return {"level": level, "reasons": reasons}


SUMMARY_SYSTEM_PROMPT = """You are a maternal health assistant summarizing a mother's
real antenatal visit data for herself, inside the Meri Aama app.

Rules:
- Use ONLY the structured data provided below. Never invent measurements, dates,
  or medical facts not present in the data.
- Never state or imply a diagnosis. You are summarizing recorded values, not
  interpreting them clinically.
- Keep tone warm, plain-language, and non-alarming -- she will read this on her
  own dashboard.
- If a section has nothing to report (e.g. no doctor notes), say so briefly
  rather than inventing content.
- Respond ONLY with valid JSON, no markdown fences, no preamble, matching:
{
  "overall_progress": "2-3 sentence plain-language summary",
  "positive_signs": ["short phrase", "..."],
  "discuss_points": ["short phrase", "..."],
  "next_visit_focus": "1 sentence"
}
"""

_FALLBACK_SUMMARY = {
    "overall_progress": "We couldn't generate a summary right now -- your visit data below is still accurate.",
    "positive_signs": [],
    "discuss_points": [],
    "next_visit_focus": "",
}


def generate_pregnancy_summary(mother, recent_visits, active_medications):
    """
    `recent_visits`: iterable of PrenatalVisit, most recent first, already
    sliced to a reasonable window (e.g. last 5) by the caller.
    """
    visit_lines = []
    for v in recent_visits:
        parts = [f"Week {v.gestational_week or '?'} ({v.visit_date})"]
        if v.maternal_weight_kg is not None:
            parts.append(f"weight {v.maternal_weight_kg}kg")
        if v.blood_pressure:
            parts.append(f"BP {v.blood_pressure}")
        if v.fetal_heart_rate_bpm:
            parts.append(f"FHR {v.fetal_heart_rate_bpm}bpm")
        if v.hemoglobin_g_dl is not None:
            parts.append(f"Hb {v.hemoglobin_g_dl}g/dL")
        if v.fundal_height_cm is not None:
            parts.append(f"fundal height {v.fundal_height_cm}cm")
        if v.edema and v.edema != "none":
            parts.append(f"edema: {v.get_edema_display()}")
        if v.urine_protein and v.urine_protein != "negative":
            parts.append(f"urine protein: {v.get_urine_protein_display()}")
        if v.doctor_notes:
            parts.append(f"note: {v.doctor_notes}")
        visit_lines.append(" | ".join(parts))

    med_lines = [
        f"{m.name} {m.dosage}, {m.adherence_percent}% adherence"
        for m in active_medications if m.is_active
    ]

    data_block = "Recent visits (most recent first):\n" + "\n".join(visit_lines or ["No visits recorded yet."])
    data_block += "\n\nActive medications:\n" + "\n".join(med_lines or ["None currently."])

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": data_block},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        parsed = json.loads(response.choices[0].message.content)
        for key in _FALLBACK_SUMMARY:
            parsed.setdefault(key, _FALLBACK_SUMMARY[key])
        return parsed
    except Exception:
        return dict(_FALLBACK_SUMMARY)