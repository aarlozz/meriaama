from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from apps.mood.models import MoodEntry
from apps.psychometric.models import PsychometricTest
from .models import InsightSuggestion
from .rules import detect_conditions, check_self_harm_flag

TREND_WINDOW_DAYS = 30


@login_required
def insights_page(request):
    """GET /insights/ -- 30-day mood trend + stress test history, plus
    condition-matched suggestions and a hardcoded self-harm safety check."""
    today = timezone.localdate()
    start_date = today - timedelta(days=TREND_WINDOW_DAYS - 1)

    mood_entries = MoodEntry.objects.filter(
        user=request.user, logged_at__date__gte=start_date
    ).order_by("logged_at")

    stress_tests = PsychometricTest.objects.filter(
        user=request.user, taken_at__date__gte=start_date
    ).order_by("taken_at")

    # Checked against her FULL test history, not just the 30-day window --
    # a concerning answer shouldn't stop being flagged just because the
    # window rolled past it.
    all_stress_tests = PsychometricTest.objects.filter(user=request.user).order_by("taken_at")
    show_crisis_banner = check_self_harm_flag(all_stress_tests)

    chart_data = _build_chart_data(mood_entries, start_date, today, stress_tests)

    active_conditions = detect_conditions(mood_entries, stress_tests)
    suggestions = InsightSuggestion.objects.filter(condition__in=active_conditions, is_active=True)

    return render(request, "insights/dashboard.html", {
        "chart_data": chart_data,
        "suggestions": suggestions,
        "show_crisis_banner": show_crisis_banner,
        "has_mood_data": mood_entries.exists(),
        "has_stress_data": stress_tests.exists(),
    })


def _build_chart_data(mood_entries, start_date, today, stress_tests):
    """Builds one row per day in the window; averages mood if multiple entries same day."""
    daily_scores = {}
    for entry in mood_entries:
        day_key = entry.logged_at.date().isoformat()
        daily_scores.setdefault(day_key, []).append(entry.score)

    labels, mood_values = [], []
    cursor = start_date
    while cursor <= today:
        iso = cursor.isoformat()
        labels.append(cursor.strftime("%b %d"))
        scores = daily_scores.get(iso)
        mood_values.append(round(sum(scores) / len(scores), 2) if scores else None)
        cursor += timedelta(days=1)

    stress_points = [
        {
            "date": test.taken_at.date().strftime("%b %d"),
            "test_type": test.get_test_type_display(),
            "risk_level": test.risk_level,
            "total_score": test.total_score,
        }
        for test in stress_tests
    ]

    return {"labels": labels, "mood_values": mood_values, "stress_points": stress_points}