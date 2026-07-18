"""
anc_clinical/schedule_rules.py

Answers "what should have happened by now that hasn't" -- separate from
flag_engine.py, which answers "is this recorded value abnormal." Pure
read functions, no signal wiring, no writes. Safe to call on every
dashboard page load.
"""
from django.utils import timezone
from django.utils import timezone
from .reference_data import (
    TRIMESTER_CHECKLIST,
    TEST_LABELS,
    SCAN_LABELS,
)
TRIMESTER_WEEK_RANGES = {1: (1, 13), 2: (14, 27), 3: (28, 45)}


def _trimester_number_for_week(week):
    if week is None:
        return None
    for tri, (lo, hi) in TRIMESTER_WEEK_RANGES.items():
        if lo <= week <= hi:
            return tri
    return None


def trimester_checklist(mother, current_week):
    """
    Returns a trimester-wise checklist showing all recommended
    laboratory tests and ultrasound scans together with their
    completion status.

    A test remains completed once it has been recorded.
    """

    from .models import LabResult, UltrasoundReport

    current_trimester = _trimester_number_for_week(current_week)

    result = []

    for trimester in (1, 2, 3):

        trimester_info = {
            "number": trimester,
            "title": f"Trimester {trimester}",
            "is_current": trimester == current_trimester,
            "is_completed": (
                current_trimester is not None
                and trimester < current_trimester
            ),
            "is_reached": (
                current_trimester is not None
                and trimester <= current_trimester
            ),
            "is_future": (
                current_trimester is not None
                and trimester > current_trimester
            ),
            "labs": [],
            "scans": [],
        }

        # --------------------------------
        # Laboratory Tests
        # --------------------------------

        for code in TRIMESTER_CHECKLIST[trimester]["labs"]:

            completed = LabResult.objects.filter(
                visit__mother=mother,
                test_code=code,
            ).exists()

            trimester_info["labs"].append({
                "code": code,
                "label": TEST_LABELS.get(code, code),
                "recorded": completed,
                "status": "Completed" if completed else "Pending",
            })

        # --------------------------------
        # Ultrasound Scans
        # --------------------------------

        for code in TRIMESTER_CHECKLIST[trimester]["scans"]:

            completed = UltrasoundReport.objects.filter(
                visit__mother=mother,
                scan_type=code,
            ).exists()

            trimester_info["scans"].append({
                "code": code,
                "label": SCAN_LABELS.get(code, code),
                "recorded": completed,
                "status": "Completed" if completed else "Pending",
            })

        result.append(trimester_info)

    return result

GROWTH_SCAN_REPEAT_DAYS = 28  # re-flag growth scan as "due" ~monthly from wk 28 on


def _is_first_visit(visit):
    from apps.hospital_portal.models import PrenatalVisit
    earliest = (
        PrenatalVisit.objects.filter(mother=visit.mother)
        .order_by("visit_date", "id")
        .first()
    )
    return earliest is not None and earliest.pk == visit.pk


def _lab_bucket(visit):
    if _is_first_visit(visit):
        return "first_visit"
    week = visit.gestational_week
    if week is not None and week >= 28:
        return "third_trimester"
    return "follow_up"  # covers <28wks and week=None


def pending_labs(visit):
    """
    [{"code", "label"}] for tests due in this visit's bucket not yet
    recorded on THIS visit. Returns [] if visit is None.
    """
    if visit is None:
        return []

    from .models import AncScheduleRule

    bucket = _lab_bucket(visit)
    rules = AncScheduleRule.objects.filter(category="lab", applies_to=bucket)
    recorded_codes = set(visit.lab_results.values_list("test_code", flat=True))

    return [{"code": r.code, "label": r.label} for r in rules if r.code not in recorded_codes]


def pending_ultrasounds(mother, current_week):
    """
    [{"code", "label", "window"}] for scan types whose window is open (or,
    for the recurring growth scan, due again) with no matching report yet.
    """
    if current_week is None:
        return []

    from .models import AncScheduleRule, UltrasoundReport

    rules = AncScheduleRule.objects.filter(category="ultrasound")
    existing = UltrasoundReport.objects.filter(visit__mother=mother)
    today = timezone.localdate()

    pending = []
    for r in rules:
        if current_week < r.week_min:
            continue

        if r.week_max is not None:
            if current_week > r.week_max:
                continue
            if existing.filter(scan_type=r.code).exists():
                continue
        else:
            last = existing.filter(scan_type=r.code).order_by("-scan_date").first()
            if last and (today - last.scan_date).days < GROWTH_SCAN_REPEAT_DAYS:
                continue

        window = f"wk {r.week_min:g}+" if r.week_max is None else f"wk {r.week_min:g}-{r.week_max:g}"
        pending.append({"code": r.code, "label": r.label, "window": window})

    return pending


def recent_risk_alerts(mother, limit=5):
    """
    Merges already-computed flags from LabResult, UltrasoundReport, and
    PrenatalVisit -- newest first. Purely a read; nothing is recomputed.
    """
    from apps.hospital_portal.models import PrenatalVisit
    from .models import LabResult, UltrasoundReport

    alerts = []

    for lr in LabResult.objects.filter(visit__mother=mother, is_flagged=True).order_by("-recorded_at")[:limit]:
        alerts.append({
            "date": lr.recorded_at.date(),
            "severity": lr.severity or "moderate",
            "text": lr.flag_reason or f"{lr.test_name} out of range",
        })

    for ur in UltrasoundReport.objects.filter(visit__mother=mother, is_flagged=True).order_by("-scan_date")[:limit]:
        alerts.append({
            "date": ur.scan_date,
            "severity": "moderate",
            "text": ur.flag_reason or f"{ur.get_scan_type_display()} flagged",
        })

    for v in PrenatalVisit.objects.filter(mother=mother, is_flagged=True).order_by("-visit_date")[:limit]:
        for reason in (v.flag_reasons or []):
            alerts.append({
                "date": v.visit_date,
                "severity": reason.get("severity", "moderate"),
                "text": reason.get("reason", ""),
            })

    alerts.sort(key=lambda a: a["date"], reverse=True)
    return alerts[:limit]