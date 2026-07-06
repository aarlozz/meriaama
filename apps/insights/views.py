from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from apps.mood.models import MoodEntry
from apps.psychometric.models import PsychometricTest

TREND_WINDOW_DAYS = 30


@login_required
def insights_page(request):
    """GET /insights/ -- 30-day mood trend + stress test history, combined into one view."""
    today = timezone.localdate()
    start_date = today - timedelta(days=TREND_WINDOW_DAYS - 1)

    mood_entries = MoodEntry.objects.filter(
        user=request.user, logged_at__date__gte=start_date
    ).order_by("logged_at")

    stress_tests = PsychometricTest.objects.filter(
        user=request.user, taken_at__date__gte=start_date
    ).order_by("taken_at")

    chart_data = _build_chart_data(mood_entries, start_date, today, stress_tests)
    insight_text = _generate_insight(mood_entries, stress_tests)

    return render(request, "insights/dashboard.html", {
        "chart_data": chart_data,
        "insight_text": insight_text,
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


def _generate_insight(mood_entries, stress_tests):
    """
    Simple rule-based summary -- NOT a diagnosis, just a plain-language
    description of the patterns in her own logged data, with a gentle nudge
    toward professional support when both signals point the same way.
    """
    mood_list = list(mood_entries)
    if len(mood_list) < 3:
        return "Keep checking in -- once you've logged a few more mood entries, we'll show you patterns here."

    today = timezone.localdate()
    last_7_cutoff = today - timedelta(days=7)
    prev_7_cutoff = today - timedelta(days=14)

    recent = [e.score for e in mood_list if e.logged_at.date() >= last_7_cutoff]
    previous = [e.score for e in mood_list if prev_7_cutoff <= e.logged_at.date() < last_7_cutoff]

    recent_avg = sum(recent) / len(recent) if recent else None
    previous_avg = sum(previous) / len(previous) if previous else None

    trend_phrase = ""
    mood_dipped = False
    if recent_avg is not None and previous_avg is not None:
        diff = recent_avg - previous_avg
        if diff <= -0.5:
            trend_phrase = "Your mood has dipped over the past week compared to the week before."
            mood_dipped = True
        elif diff >= 0.5:
            trend_phrase = "Your mood has improved over the past week compared to the week before."
        else:
            trend_phrase = "Your mood has stayed fairly steady over the past two weeks."
    elif recent_avg is not None:
        trend_phrase = f"Your average mood over the past week is {recent_avg:.1f} out of 5."

    latest_test = stress_tests.order_by("-taken_at").first()
    risk_phrase = ""
    concerning_risk = False
    if latest_test:
        risk_phrase = f" Your most recent {latest_test.get_test_type_display()} result showed {latest_test.get_risk_level_display().lower()} risk."
        concerning_risk = latest_test.risk_level in ("high", "moderate")

    combined = trend_phrase + risk_phrase

    if mood_dipped and concerning_risk:
        combined += (
            " Since both your mood and your recent stress test point the same way, "
            "it might help to talk to a doctor about how you've been feeling."
        )
    elif not stress_tests.exists():
        combined += " You haven't taken a stress test yet -- it can add useful context alongside your mood trend."

    return combined