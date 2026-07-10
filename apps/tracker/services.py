"""
Weight-gain trend analysis and weekly baby fact lookup. Weight data comes
ONLY from staff-verified apps.hospital_portal.PrenatalVisit records, not
any self-reported source. The recommended range is a standard published
guideline, not app-generated advice.
"""
from .models import WeeklyBabyFact


def build_weight_series(profile, visits):
    weight_range = profile.recommended_weight_gain_range_kg
    if weight_range is None or not profile.pre_pregnancy_weight_kg:
        return None

    sorted_visits = sorted(visits, key=lambda v: v.visit_date)
    labels, weights, gains = [], [], []
    baseline = float(profile.pre_pregnancy_weight_kg)

    for v in sorted_visits:
        if v.maternal_weight_kg is None:
            continue
        labels.append(v.visit_date.strftime("%b %d"))
        weights.append(float(v.maternal_weight_kg))
        gains.append(round(float(v.maternal_weight_kg) - baseline, 1))

    if not weights:
        return None

    latest_gain = gains[-1]
    min_gain, max_gain = weight_range
    status = "below" if latest_gain < min_gain else "above" if latest_gain > max_gain else "on_track"

    return {
        "labels": labels, "weights": weights, "gains": gains, "baseline_weight": baseline,
        "min_recommended_gain": min_gain, "max_recommended_gain": max_gain,
        "latest_gain": latest_gain, "status": status,
    }


def get_weekly_baby_fact(gestational_week):
    """Matches ANY row whose range contains her current week -- always finds
    something as long as the seed data has full, contiguous coverage."""
    if not gestational_week:
        return None
    return WeeklyBabyFact.objects.filter(
        start_week__lte=gestational_week,
        end_week__gte=gestational_week,
        is_active=True,
    ).order_by("start_week").first()