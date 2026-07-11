from .models import WeeklyBabyFact


def build_weight_series(profile, visits):
    """
    Build chart data using ONLY hospital-recorded PrenatalVisit weights.
    """

    if not profile:
        return None

    recommended_range = profile.recommended_weight_gain_range_kg

    if recommended_range is None or profile.pre_pregnancy_weight_kg is None:
        return None

    visits = sorted(visits, key=lambda visit: visit.visit_date)

    baseline = float(profile.pre_pregnancy_weight_kg)

    labels = []
    weights = []
    gains = []

    for visit in visits:

        if visit.maternal_weight_kg is None:
            continue

        labels.append(visit.visit_date.strftime("%b %d"))

        weight = float(visit.maternal_weight_kg)
        weights.append(weight)
        gains.append(round(weight - baseline, 1))

    if not weights:
        return None

    latest_gain = gains[-1]
    min_gain, max_gain = recommended_range

    if latest_gain < min_gain:
        status = "below"
    elif latest_gain > max_gain:
        status = "above"
    else:
        status = "on_track"

    return {
        "labels": labels,
        "weights": weights,
        "gains": gains,
        "baseline_weight": baseline,
        "latest_gain": latest_gain,
        "status": status,
        "min_recommended_gain": min_gain,
        "max_recommended_gain": max_gain,
    }


def get_weekly_baby_fact(week):
    """
    Returns the educational content for the mother's
    current gestational week.
    """

    if not week:
        return None

    return (
        WeeklyBabyFact.objects.filter(
            start_week__lte=week,
            end_week__gte=week,
            is_active=True,
        )
        .order_by("start_week")
        .first()
    )


def pregnancy_progress(profile):
    """
    Calculates pregnancy progress statistics for dashboard cards.
    """

    if not profile:
        return None

    week = profile.current_gestational_week

    if not week:
        return None

    total_weeks = 40

    progress = min(round((week / total_weeks) * 100), 100)

    trimester = 1 if week <= 13 else 2 if week <= 27 else 3

    weeks_left = max(40 - week, 0)

    return {
        "week": week,
        "trimester": trimester,
        "progress": progress,
        "weeks_left": weeks_left,
    }


def medication_summary(medications):
    """
    Aggregate dashboard summary cards, and attach per-medication
    computed stats (remaining_doses) so the template never has to
    do arithmetic itself (Django template filters can't subtract).
    """

    medications = list(medications)

    if not medications:
        return {
            "active": 0,
            "completed": 0,
            "overall_adherence": 0,
            "total_doses_taken": 0,
        }

    active = sum(medication.is_active for medication in medications)
    completed = len(medications) - active

    adherence_values = [medication.adherence_percent for medication in medications]
    adherence = round(sum(adherence_values) / len(adherence_values))

    total_doses_taken = 0

    for medication in medications:
        remaining = medication.total_expected_doses - medication.taken_doses_count
        medication.remaining_doses = max(remaining, 0)
        total_doses_taken += medication.taken_doses_count

    return {
        "active": active,
        "completed": completed,
        "overall_adherence": adherence,
        "total_doses_taken": total_doses_taken,
    }