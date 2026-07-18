from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from apps.anc_clinical import schedule_rules

TRIMESTER_RANGES = [(1, 1, 13), (2, 14, 27), (3, 28, 45)]

MILESTONES = [
    (0, "Pregnancy confirmed"),
    (13, "First trimester complete"),
    (20, "Anatomy scan time"),
    (28, "Third trimester begins"),
    (37, "Full term"),
]

DIPSTICK_TEXT = {"negative", "trace", "plus1", "plus2", "plus3"}
REACTIVE_TEXT = {"reactive", "non_reactive"}


def _trimester_for_week(week):
    if week is None:
        return None
    for label, lo, hi in TRIMESTER_RANGES:
        if lo <= week <= hi:
            return label
    return None


def _is_hospital_staff(user):
    return user.is_authenticated and (user.is_hospital_staff() or user.is_hospital_admin())


@login_required
def pregnancy_dashboard(request):
    mother = request.user
    profile = getattr(mother, "health_profile", None)

    visits = list(mother.prenatal_visits.all())
    latest_visit = visits[0] if visits else None
    medications = list(mother.medications.all())

    week = profile.current_gestational_week if profile else None
    trimester = _trimester_for_week(week)

    # ---- Care checklist data (read-only, additive) ----
    pending_labs = schedule_rules.pending_labs(latest_visit)
    pending_scans = schedule_rules.pending_ultrasounds(mother, week)
    risk_alerts = schedule_rules.recent_risk_alerts(mother)
    trimester_data = schedule_rules.trimester_checklist(mother, week)

    # Calculate progress for each trimester
    # FIX: this used to sit half-inside/half-outside the loop, so completed/
    # total/percent only ever got set on the LAST trimester in the list.
    # Everything now runs once per trimester, inside the loop.
    for tri in trimester_data:
        total = len(tri["labs"]) + len(tri["scans"])
        completed = (
            sum(1 for item in tri["labs"] if item["recorded"])
            + sum(1 for item in tri["scans"] if item["recorded"])
        )
        tri["completed"] = completed
        tri["total"] = total
        tri["percent"] = round((completed / total) * 100) if total else 0

    lmp_missing = profile is None or not profile.last_menstrual_period

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
    journey.reverse()

    # ---- trimester snapshot ----
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
        "medications": active_medications,
        "charts": charts,
        "journey": journey,
        "snapshot": snapshot,
        "milestones": milestones,
        "doctor_notes": doctor_notes,
        "visit_count": len(visits),
        "active_nav": "pregnancy_dashboard",
        "pending_labs": pending_labs,
        "pending_scans": pending_scans,
        "risk_alerts": risk_alerts,
        "trimester_data": trimester_data,
        "lmp_missing": lmp_missing,
    }
    return render(request, "pregnancy_dashboard/dashboard.html", context)