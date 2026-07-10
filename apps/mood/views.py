from datetime import date, timedelta
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from .models import MoodEntry
from .forms import MoodEntryForm


def _score_bucket(avg_score):
    if avg_score is None:
        return "empty"
    if avg_score < 1.5:
        return "very-low"
    if avg_score < 2.5:
        return "low"
    if avg_score < 3.5:
        return "neutral"
    if avg_score < 4.5:
        return "good"
    return "very-good"


def _build_mood_heatmap(user, weeks=18):
    """
    One aggregate query total -- never touches individual MoodEntry rows,
    so this stays fast whether the user has 10 entries or 10,000.
    Returns [(week, month_label), ...], each week a list of 7 day-dicts,
    Sunday-start, covering the last `weeks` weeks up to today.
    """
    today = date.today()
    end_date = today
    start_date = end_date - timedelta(days=weeks * 7 - 1)
    start_weekday = (start_date.weekday() + 1) % 7  # Sunday=0 ... Saturday=6
    start_date -= timedelta(days=start_weekday)

    daily = (
        MoodEntry.objects.filter(user=user, logged_at__date__gte=start_date, logged_at__date__lte=end_date)
        .annotate(day=TruncDate("logged_at"))
        .values("day")
        .annotate(avg_score=Avg("score"), entry_count=Count("id"))
    )
    by_day = {row["day"]: row for row in daily}

    grid, week, current = [], [], start_date
    while current <= end_date:
        row = by_day.get(current)
        avg_score = row["avg_score"] if row else None
        week.append({
            "date": current,
            "count": row["entry_count"] if row else 0,
            "bucket": _score_bucket(avg_score),
            "is_future": current > today,
        })
        if len(week) == 7:
            grid.append(week)
            week = []
        current += timedelta(days=1)
    if week:
        grid.append(week)

    month_labels = []
    for w in grid:
        label = ""
        for day in w:
            if day["date"].day == 1 or day["date"] == start_date:
                label = day["date"].strftime("%b")
                break
        month_labels.append(label)

    return list(zip(grid, month_labels))


@login_required
def mood_checkin_page(request):
    """GET/POST /mood/ -- log today's mood + browse history via heatmap + paginated list."""
    if request.method == "POST":
        form = MoodEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            messages.success(request, "Mood logged. Thank you for checking in.")
            return redirect("mood-checkin")
    else:
        form = MoodEntryForm()

    entries = MoodEntry.objects.filter(user=request.user)

    filter_date_str = request.GET.get("date", "")
    filter_date = None
    if filter_date_str:
        try:
            filter_date = date.fromisoformat(filter_date_str)
            entries = entries.filter(logged_at__date=filter_date)
        except ValueError:
            filter_date = None

    paginator = Paginator(entries, 10)
    history = paginator.get_page(request.GET.get("page"))
    heatmap = _build_mood_heatmap(request.user)

    return render(request, "mood/checkin.html", {
        "form": form, "history": history, "heatmap": heatmap, "filter_date": filter_date,"header_title": "Mood Tracker",
"header_subtitle": "Track your emotional wellbeing every day",
    })