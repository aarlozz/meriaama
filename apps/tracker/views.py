from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import WeeklyUpdate


@login_required
def weekly_tracker_page(request):
    """GET /tracker/ -- every weekly entry logged for the mother, oldest to newest."""
    weeks = WeeklyUpdate.objects.filter(user=request.user).order_by("gestational_week")

    # Safe no-op if you haven't built a health_profile app with this field yet.
    current_week = None
    profile = getattr(request.user, "health_profile", None)
    if profile:
        current_week = getattr(profile, "current_gestational_week", None)

    return render(request, "tracker/weeks.html", {
        "weeks": weeks,
        "current_week": current_week,
    })