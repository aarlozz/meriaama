from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import calculate_risk, generate_pregnancy_summary

# (label, low_week, high_week) -- adjust high bound on trimester 3 if you
# want to cap it differently for post-term tracking
TRIMESTER_RANGES = [(1, 1, 13), (2, 14, 27), (3, 28, 45)]

MILESTONES = [
    (0, "Pregnancy confirmed"),
    (13, "First trimester complete"),
    (20, "Anatomy scan time"),
    (28, "Third trimester begins"),
    (37, "Full term"),
]


def _trimester_for_week(week):
    if week is None:
        return None
    for label, lo, hi in TRIMESTER_RANGES:
        if lo <= week <= hi:
            return label
    return None


@login_required
def pregnancy_dashboard(request):
    mother = request.user
    profile = getattr(mother, "health_profile", None)

    visits = list(mother.prenatal_visits.all())  # PrenatalVisit.Meta.ordering = -visit_date
    latest_visit = visits[0] if visits else None
    medications = list(mother.medications.all())

    week = profile.current_gestational_week if profile else None
    trimester = _trimester_for_week(week)

    risk = calculate_risk(mother)
    ai_summary = generate_pregnancy_summary(mother, visits[:5], medications)

    # ---- chart series, oldest -> newest ----
    chrono = list(reversed(visits))
    charts = {
        "labels": [
            (f"Wk {v.gestational_week}" if v.gestational_week else v.visit_date.strftime("%b %d"))
            for v in chrono
        ],
        "weight": [float(v.maternal_weight_kg) if v.maternal_weight_kg is not None else None for v in chrono],
        "hemoglobin": [float(v.hemoglobin_g_dl) if v.hemoglobin_g_dl is not None else None for v in chrono],
        "fetal_heart_rate": [v.fetal_heart_rate_bpm for v in chrono],
        "fundal_height": [float(v.fundal_height_cm) if v.fundal_height_cm is not None else None for v in chrono],
        "bp_systolic": [],
        "bp_diastolic": [],
    }
    for v in chrono:
        sys_val, dia_val = None, None
        if v.blood_pressure and "/" in v.blood_pressure:
            try:
                s, d = v.blood_pressure.split("/")
                sys_val, dia_val = int(s), int(d)
            except ValueError:
                pass
        charts["bp_systolic"].append(sys_val)
        charts["bp_diastolic"].append(dia_val)

    # ---- pregnancy journey timeline ----
    journey = []
    for i, v in enumerate(chrono):
        highlights = []
        if i == 0:
            highlights.append("First antenatal visit recorded")
        if v.fetal_heart_rate_bpm:
            highlights.append(f"Baby's heartbeat recorded at {v.fetal_heart_rate_bpm} bpm")
        if v.hemoglobin_g_dl is not None and float(v.hemoglobin_g_dl) < 11:
            highlights.append("Hemoglobin noted slightly low")
        if v.fetal_position and v.fetal_position not in ("", "not_assessed"):
            highlights.append(f"Baby's position: {v.get_fetal_position_display()}")
        if not highlights:
            highlights.append("Routine checkup recorded")
        journey.append({"week": v.gestational_week, "date": v.visit_date, "highlights": highlights})
    journey.reverse()  # show newest first, matches rest of the app's convention

    # ---- trimester snapshot (counts + weight delta) ----
    snapshot = {}
    for label, lo, hi in TRIMESTER_RANGES:
        t_visits = [v for v in chrono if v.gestational_week and lo <= v.gestational_week <= hi]
        weights = [float(v.maternal_weight_kg) for v in t_visits if v.maternal_weight_kg is not None]
        snapshot[label] = {
            "visit_count": len(t_visits),
            "weight_change": round(weights[-1] - weights[0], 1) if len(weights) >= 2 else None,
            "has_data": bool(t_visits),
        }

    milestones = [
        {"week": w, "label": label, "reached": bool(week and week >= w)}
        for w, label in MILESTONES
    ]

    doctor_notes = [v for v in visits if v.doctor_notes][:3]
    active_medications = [m for m in medications if m.is_active]

    context = {
        "profile": profile,
        "week": week,
        "trimester": trimester,
        "latest_visit": latest_visit,
        "next_visit_date": latest_visit.next_visit_date if latest_visit else None,
        "risk": risk,
        "ai_summary": ai_summary,
        "medications": active_medications,
        "charts": charts,
        "journey": journey,
        "snapshot": snapshot,
        "milestones": milestones,
        "doctor_notes": doctor_notes,
        "visit_count": len(visits),
        "active_nav": "pregnancy_dashboard",
    }
    return render(request, "pregnancy_dashboard/dashboard.html", context)