from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from .models import PersonalCheckIn, MedicationLog, DoctorQuestion
from .forms import PersonalCheckInForm, DoctorQuestionForm
from .services import build_weight_series, get_weekly_baby_fact
from apps.hospital_portal.models import PrenatalVisit, Medication


@login_required
def tracker_page(request):
    """GET/POST /tracker/ -- combined timeline, medications, doctor questions,
    weight trend, and baby development content for her current week."""
    profile = getattr(request.user, "health_profile", None)

    if request.method == "POST":
        form = PersonalCheckInForm(request.POST, request.FILES)
        if form.is_valid():
            checkin = form.save(commit=False)
            checkin.user = request.user
            checkin.save()
            messages.success(request, "Note saved.")
            return redirect("tracker")
    else:
        form = PersonalCheckInForm()

    visits = list(PrenatalVisit.objects.filter(mother=request.user))
    checkins = list(PersonalCheckIn.objects.filter(user=request.user))
    medications = Medication.objects.filter(mother=request.user).order_by("-start_date")
    questions = DoctorQuestion.objects.filter(user=request.user)

    type_filter = request.GET.get("type", "all")
    items = []
    if type_filter in ("all", "visit"):
        items += [{"type": "visit", "date": v.visit_date, "obj": v} for v in visits]
    if type_filter in ("all", "checkin"):
        items += [{"type": "checkin", "date": c.logged_at.date(), "obj": c} for c in checkins]
    items.sort(key=lambda item: item["date"], reverse=True)

    paginator = Paginator(items, 20)  # bumped up since rows are compact now
    timeline = paginator.get_page(request.GET.get("page"))

    next_visit = PrenatalVisit.objects.filter(mother=request.user).exclude(
        next_visit_date__isnull=True
    ).order_by("-visit_date").first()
    next_visit_date = next_visit.next_visit_date if next_visit else None
    is_overdue = bool(next_visit_date and next_visit_date < timezone.localdate())

    weight_data = build_weight_series(profile, visits) if profile else None
    baby_fact = get_weekly_baby_fact(profile.current_gestational_week) if profile else None

    week = getattr(profile, "current_gestational_week", None)
    if week:
        subtitle = f"Week {week} of your pregnancy"
    else:
        subtitle = "Monitor your pregnancy journey week by week"

    return render(request, "tracker/timeline.html", {
        "form": form, "timeline": timeline, "type_filter": type_filter,
        "medications": medications, "questions": questions,
        "next_visit_date": next_visit_date, "is_overdue": is_overdue,
        "profile": profile, "weight_data": weight_data, "baby_fact": baby_fact,
        "header_subtitle": subtitle,
        "header_title": "Pregnancy Tracker",
    })


@login_required
def edit_checkin(request, checkin_id):
    checkin = get_object_or_404(PersonalCheckIn, id=checkin_id, user=request.user)
    if request.method == "POST":
        form = PersonalCheckInForm(request.POST, request.FILES, instance=checkin)
        if form.is_valid():
            form.save()
            messages.success(request, "Note updated.")
            return redirect("tracker")
    else:
        form = PersonalCheckInForm(instance=checkin)
    return render(request, "tracker/edit_checkin.html", {"form": form, "checkin": checkin})


@login_required
def delete_checkin(request, checkin_id):
    checkin = get_object_or_404(PersonalCheckIn, id=checkin_id, user=request.user)
    if request.method == "POST":
        checkin.delete()
        messages.success(request, "Note deleted.")
    return redirect("tracker")


@login_required
def mark_dose_taken(request, medication_id):
    medication = get_object_or_404(Medication, id=medication_id, mother=request.user)
    if request.method == "POST":
        MedicationLog.objects.create(medication=medication, date=timezone.localdate())
        messages.success(request, f"Marked a dose of {medication.name} as taken.")
    return redirect("tracker")


@login_required
def add_question(request):
    if request.method == "POST":
        form = DoctorQuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.user = request.user
            question.save()
            messages.success(request, "Question added.")
    return redirect("tracker")


@login_required
def toggle_question(request, question_id):
    question = get_object_or_404(DoctorQuestion, id=question_id, user=request.user)
    if request.method == "POST":
        question.is_answered = not question.is_answered
        question.save(update_fields=["is_answered"])
    return redirect("tracker")


@login_required
def delete_question(request, question_id):
    question = get_object_or_404(DoctorQuestion, id=question_id, user=request.user)
    if request.method == "POST":
        question.delete()
    return redirect("tracker")