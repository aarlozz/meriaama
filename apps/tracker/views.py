from itertools import chain
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import PersonalCheckIn, MedicationLog
from .forms import PersonalCheckInForm
from apps.hospital_portal.models import PrenatalVisit, Medication


@login_required
def tracker_page(request):
    """GET/POST /tracker/ -- combined timeline (staff visits + her own private
    notes), current medications with adherence tracking, next-visit reminder."""
    if request.method == "POST":
        form = PersonalCheckInForm(request.POST)
        if form.is_valid():
            checkin = form.save(commit=False)
            checkin.user = request.user
            checkin.save()
            messages.success(request, "Note saved.")
            return redirect("tracker")
    else:
        form = PersonalCheckInForm()

    visits = PrenatalVisit.objects.filter(mother=request.user)
    checkins = PersonalCheckIn.objects.filter(user=request.user)
    medications = Medication.objects.filter(mother=request.user).order_by("-start_date")

    timeline = sorted(
        chain(
            ({"type": "visit", "date": v.visit_date, "obj": v} for v in visits),
            ({"type": "checkin", "date": c.logged_at.date(), "obj": c} for c in checkins),
        ),
        key=lambda item: item["date"], reverse=True,
    )

    next_visit = visits.exclude(next_visit_date__isnull=True).order_by("-visit_date").first()
    next_visit_date = next_visit.next_visit_date if next_visit else None
    is_overdue = bool(next_visit_date and next_visit_date < timezone.localdate())

    return render(request, "tracker/timeline.html", {
        "form": form, "timeline": timeline, "medications": medications,
        "next_visit_date": next_visit_date, "is_overdue": is_overdue,
        "header_title": "Pregnancy Tracker",
"header_subtitle": "Monitor your pregnancy journey week by week",
        
    })


@login_required
def mark_dose_taken(request, medication_id):
    """POST /tracker/medication/<id>/mark-taken/ -- log one dose taken today."""
    medication = get_object_or_404(Medication, id=medication_id, mother=request.user)
    if request.method == "POST":
        MedicationLog.objects.create(medication=medication, date=timezone.localdate())
        messages.success(request, f"Marked a dose of {medication.name} as taken.")
    return redirect("tracker")