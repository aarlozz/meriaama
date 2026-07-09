from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Q
from .models import PrenatalVisit, TRACKED_FIELDS
from .forms import PrenatalVisitForm, StaffHealthProfileForm
from .models import PrenatalVisit, Medication

User = get_user_model()


def hospital_staff_required(view_func):
    """Like @login_required, but also checks role is doctor/nurse/data_entry OR admin."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_hospital_staff() or request.user.is_hospital_admin()):
            return HttpResponseForbidden("This page is for hospital staff only.")
        return view_func(request, *args, **kwargs)
    return wrapper


def hospital_admin_required(view_func):
    """Stricter than hospital_staff_required -- admin only (for approvals)."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_hospital_admin():
            return HttpResponseForbidden("This page is for hospital admins only.")
        return view_func(request, *args, **kwargs)
    return wrapper


@hospital_staff_required
def staff_dashboard(request):
    """
    GET /hospital/ -- search mothers by username or phone number.
    Admins additionally see a pending-approvals count and a full mother list
    by default (not just search results).
    """
    query = request.GET.get("q", "").strip()
    if query:
        results = User.objects.filter(role=User.Role.MOTHER).filter(
            Q(username__icontains=query) | Q(phone_number__icontains=query)
        )
    elif request.user.is_hospital_admin():
        results = User.objects.filter(role=User.Role.MOTHER)
    else:
        results = []

    pending_count = 0
    if request.user.is_hospital_admin():
        pending_count = User.objects.filter(
            role__in=[User.Role.DATA_ENTRY],
            is_active=False,
        ).count()

    return render(request, "hospital_portal/dashboard.html", {
        "query": query,
        "results": results,
        "pending_count": pending_count,
    })


def _completeness_checklist(visits):
    """For each of the 10 tracked fields, has it EVER been recorded across her visits?"""
    checklist = []
    for field_name, label in TRACKED_FIELDS:
        recorded = any(getattr(v, field_name) not in (None, "") for v in visits)
        checklist.append({"label": label, "recorded": recorded})
    return checklist


@hospital_staff_required
def mother_detail(request, mother_id):
    """GET /hospital/mother/<id>/ -- her clinical profile + visit history + completeness checklist."""
    mother = get_object_or_404(User, id=mother_id, role=User.Role.MOTHER)
    profile = getattr(mother, "health_profile", None)
    visits = list(PrenatalVisit.objects.filter(mother=mother))
    medications = Medication.objects.filter(mother=mother) 

    return render(request, "hospital_portal/mother_detail.html", {
        "mother": mother,
        "profile": profile,
        "visits": visits,
        "checklist": _completeness_checklist(visits),
        "medications": medications,  # NEW
    })


@hospital_staff_required
def edit_health_profile(request, mother_id):
    """GET/POST /hospital/mother/<id>/edit-profile/ -- staff edits shared clinical fields."""
    mother = get_object_or_404(User, id=mother_id, role=User.Role.MOTHER)
    profile = getattr(mother, "health_profile", None)
    if profile is None:
        messages.error(request, "This mother hasn't created a health profile yet.")
        return redirect("hospital-mother-detail", mother_id=mother.id)

    if request.method == "POST":
        form = StaffHealthProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Health profile updated.")
            return redirect("hospital-mother-detail", mother_id=mother.id)
    else:
        form = StaffHealthProfileForm(instance=profile)

    return render(request, "hospital_portal/edit_health_profile.html", {"form": form, "mother": mother})


@hospital_staff_required
def add_visit(request, mother_id):
    """GET/POST /hospital/mother/<id>/add-visit/ -- record a new clinical visit."""
    mother = get_object_or_404(User, id=mother_id, role=User.Role.MOTHER)

    if request.method == "POST":
        form = PrenatalVisitForm(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.mother = mother
            visit.entered_by = request.user
            visit.save()
            messages.success(request, "Visit recorded.")
            return redirect("hospital-mother-detail", mother_id=mother.id)
    else:
        profile = getattr(mother, "health_profile", None)
        initial = {"gestational_week": getattr(profile, "current_gestational_week", None)}
        form = PrenatalVisitForm(initial=initial)

    return render(request, "hospital_portal/add_visit.html", {"form": form, "mother": mother})


@hospital_admin_required
def staff_approvals(request):
    """GET /hospital/approvals/ -- list pending staff accounts for admin to approve/reject."""
    pending = User.objects.filter(
        role__in=[User.Role.DATA_ENTRY],
        is_active=False,
    )
    return render(request, "hospital_portal/approvals.html", {"pending": pending})


@hospital_admin_required
def approve_staff(request, user_id):
    """POST /hospital/approvals/<id>/approve/"""
    staff = get_object_or_404(User, id=user_id, is_active=False)
    if request.method == "POST":
        staff.is_active = True
        staff.save(update_fields=["is_active"])
        messages.success(request, f"{staff.username} has been approved.")
    return redirect("hospital-staff-approvals")


@hospital_admin_required
def reject_staff(request, user_id):
    """POST /hospital/approvals/<id>/reject/ -- deletes the pending account."""
    staff = get_object_or_404(User, id=user_id, is_active=False)
    if request.method == "POST":
        username = staff.username
        staff.delete()
        messages.success(request, f"{username}'s registration was rejected and removed.")
    return redirect("hospital-staff-approvals")


from .forms import PrenatalVisitForm, StaffHealthProfileForm, MedicationForm

@hospital_staff_required
def prescribe_medication(request, mother_id):
    """GET/POST /hospital/mother/<id>/prescribe/ -- start a new medication course."""
    mother = get_object_or_404(User, id=mother_id, role=User.Role.MOTHER)

    if request.method == "POST":
        form = MedicationForm(request.POST)
        if form.is_valid():
            medication = form.save(commit=False)
            medication.mother = mother
            medication.prescribed_by = request.user
            medication.save()
            messages.success(request, f"{medication.name} prescribed for {medication.duration_days} days.")
            return redirect("hospital-mother-detail", mother_id=mother.id)
    else:
        form = MedicationForm()

    return render(request, "hospital_portal/prescribe_medication.html", {"form": form, "mother": mother})