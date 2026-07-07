from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import PersonalCheckIn
from .forms import PersonalCheckInForm


@login_required
def tracker_page(request):
    """GET/POST /tracker/ -- combined timeline of staff visits + her own notes, plus next-visit reminder."""
    if request.method == "POST":
        form = PersonalCheckInForm(request.POST)
        if form.is_valid():
            checkin = form.save(commit=False)
            checkin.user = request.user
            checkin.save()
            messages.success(request, "Your note has been saved.")
            return redirect("weekly-tracker")
    else:
        form = PersonalCheckInForm()

    # Staff-entered visits -- imported here (not at module level) to keep
    # tracker usable even if hospital_portal isn't installed yet.
    try:
        from apps.hospital_portal.models import PrenatalVisit
        staff_visits = PrenatalVisit.objects.filter(mother=request.user)
    except Exception:
        staff_visits = []

    personal_notes = PersonalCheckIn.objects.filter(user=request.user)

    timeline = []
    for visit in staff_visits:
        timeline.append({"kind": "staff_visit", "date": visit.visit_date, "obj": visit})
    for note in personal_notes:
        timeline.append({"kind": "personal_note", "date": note.visit_date, "obj": note})
    timeline.sort(key=lambda item: item["date"], reverse=True)

    # Next-visit reminder: soonest upcoming next_visit_date across staff visits
    today = date.today()
    upcoming = [v.next_visit_date for v in staff_visits if v.next_visit_date and v.next_visit_date >= today]
    next_visit_date = min(upcoming) if upcoming else None

    return render(request, "tracker/timeline.html", {
        "form": form,
        "timeline": timeline,
        "next_visit_date": next_visit_date,
    })