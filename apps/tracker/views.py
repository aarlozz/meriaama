from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import (
    PersonalCheckInForm,
    DoctorQuestionForm,
)

from .models import (
    PersonalCheckIn,
    MedicationLog,
    DoctorQuestion,
)

from .services import (
    build_weight_series,
    get_weekly_baby_fact,
    pregnancy_progress,
    medication_summary,
)

from apps.hospital_portal.models import (
    PrenatalVisit,
    Medication,
)

VALID_TIMELINE_TYPES = ("all", "visit", "checkin")


@login_required
def tracker_page(request):
    """
    Pregnancy Tracker Dashboard

    Combines:

    • Pregnancy progress
    • Weekly baby development
    • Weight chart
    • Medication dashboard
    • Timeline
    • Doctor questions
    • Personal notes
    """

    profile = getattr(request.user, "health_profile", None)

    # -------------------------
    # Save Personal Note
    # -------------------------

    if request.method == "POST":

        form = PersonalCheckInForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            note = form.save(commit=False)
            note.user = request.user
            note.save()

            messages.success(
                request,
                "Your private note has been saved."
            )

            return redirect("tracker")

    else:

        form = PersonalCheckInForm()

    # -------------------------
    # Database Queries
    # -------------------------

    visits = list(
        PrenatalVisit.objects.filter(
            mother=request.user
        ).order_by("-visit_date")
    )

    checkins = list(
        PersonalCheckIn.objects.filter(
            user=request.user
        )
    )

    # prefetch_related("logs") avoids an N+1 query for every
    # per-medication property (adherence_percent, taken_doses_count,
    # expected_doses_so_far, day_number) that reads medication.logs.
    medications = list(
        Medication.objects.filter(
            mother=request.user
        )
        .order_by("-start_date")
        .prefetch_related("logs")
    )

    questions = DoctorQuestion.objects.filter(
        user=request.user
    )

    # -------------------------
    # Timeline Filter
    # -------------------------

    type_filter = request.GET.get("type", "all")

    if type_filter not in VALID_TIMELINE_TYPES:
        type_filter = "all"

    timeline_items = []

    if type_filter in ("all", "visit"):

        for visit in visits:

            timeline_items.append({
                "type": "visit",
                "date": visit.visit_date,
                "obj": visit,
            })

    if type_filter in ("all", "checkin"):

        for note in checkins:

            timeline_items.append({
                "type": "checkin",
                "date": note.logged_at.date(),
                "obj": note,
            })

    timeline_items.sort(
        key=lambda item: item["date"],
        reverse=True,
    )

    paginator = Paginator(
        timeline_items,
        20,
    )

    timeline = paginator.get_page(
        request.GET.get("page")
    )

    # -------------------------
    # Next Visit
    # -------------------------

    latest_visit = (
        PrenatalVisit.objects.filter(
            mother=request.user
        )
        .exclude(
            next_visit_date__isnull=True
        )
        .order_by("-visit_date")
        .first()
    )

    next_visit_date = (
        latest_visit.next_visit_date
        if latest_visit
        else None
    )

    is_overdue = bool(
        next_visit_date
        and next_visit_date < timezone.localdate()
    )

    # -------------------------
    # Dashboard Data
    # -------------------------

    weight_data = (
        build_weight_series(profile, visits)
        if profile
        else None
    )

    baby_fact = (
        get_weekly_baby_fact(profile.current_gestational_week)
        if profile
        else None
    )

    pregnancy = pregnancy_progress(profile)

    # medications is already a concrete list here, so medication_summary()
    # attaches remaining_doses to the exact same objects the template
    # iterates over -- no reliance on queryset result-cache behavior.
    medicine_dashboard = medication_summary(medications)

    # -------------------------
    # Header
    # -------------------------

    if pregnancy:

        header_title = (
            f"Week {pregnancy['week']} Pregnancy Tracker"
        )

        header_subtitle = (
            f"{pregnancy['weeks_left']} weeks remaining • "
            f"{pregnancy['progress']}% completed"
        )

    else:

        header_title = "Pregnancy Tracker"
        header_subtitle = "Track your pregnancy journey"

    # -------------------------
    # Render
    # -------------------------

    return render(
        request,
        "tracker/timeline.html",
        {
            "form": form,
            "timeline": timeline,
            "type_filter": type_filter,
            "profile": profile,
            "questions": questions,
            "medications": medications,
            "weight_data": weight_data,
            "baby_fact": baby_fact,
            "pregnancy": pregnancy,
            "medicine_dashboard": medicine_dashboard,
            "next_visit_date": next_visit_date,
            "is_overdue": is_overdue,
            "header_title": header_title,
            "header_subtitle": header_subtitle,
        },
    )


@login_required
def edit_checkin(request, checkin_id):
    """
    Edit one private pregnancy note.
    """

    checkin = get_object_or_404(
        PersonalCheckIn,
        id=checkin_id,
        user=request.user,
    )

    if request.method == "POST":

        form = PersonalCheckInForm(
            request.POST,
            request.FILES,
            instance=checkin,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Your note has been updated.",
            )

            return redirect("tracker")

    else:

        form = PersonalCheckInForm(
            instance=checkin
        )

    return render(
        request,
        "tracker/edit_checkin.html",
        {
            "form": form,
            "checkin": checkin,
        },
    )


@login_required
def delete_checkin(request, checkin_id):
    """
    Delete a private note.
    """

    checkin = get_object_or_404(
        PersonalCheckIn,
        id=checkin_id,
        user=request.user,
    )

    if request.method == "POST":

        checkin.delete()

        messages.success(
            request,
            "Your private note has been deleted.",
        )

    return redirect("tracker")


@login_required
def mark_dose_taken(request, medication_id):
    """
    Record one medication dose.
    """

    medication = get_object_or_404(
        Medication,
        id=medication_id,
        mother=request.user,
    )

    if request.method == "POST":

        MedicationLog.objects.create(
            medication=medication,
            date=timezone.localdate(),
        )

        messages.success(
            request,
            f"{medication.name} marked as taken.",
        )

    return redirect("tracker")


@login_required
def add_question(request):
    """
    Save a question for the next prenatal visit.
    """

    if request.method == "POST":

        form = DoctorQuestionForm(
            request.POST
        )

        if form.is_valid():

            question = form.save(commit=False)
            question.user = request.user
            question.save()

            messages.success(
                request,
                "Question added for your next visit.",
            )

    return redirect("tracker")


@login_required
def toggle_question(request, question_id):
    """
    Mark question answered/unanswered.
    """

    question = get_object_or_404(
        DoctorQuestion,
        id=question_id,
        user=request.user,
    )

    if request.method == "POST":

        question.is_answered = not question.is_answered

        question.save(
            update_fields=["is_answered"]
        )

    return redirect("tracker")


@login_required
def delete_question(request, question_id):
    """
    Delete a saved doctor question.
    """

    question = get_object_or_404(
        DoctorQuestion,
        id=question_id,
        user=request.user,
    )

    if request.method == "POST":

        question.delete()

        messages.success(
            request,
            "Question removed.",
        )

    return redirect("tracker")