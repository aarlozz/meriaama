from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Q
from .models import PrenatalVisit, TRACKED_FIELDS
from .forms import PrenatalVisitForm, StaffHealthProfileForm

User = get_user_model()


def hospital_staff_required(view_func):
    """Like @login_required, but also checks role is doctor/nurse/data_entry."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_hospital_staff():
            return HttpResponseForbidden("This page is for hospital staff only.")
        return view_func(request, *args, **kwargs)
    return wrapper


@hospital_staff_required
def staff_dashboard(request):
    """GET /hospital/ -- search mothers by username or phone number."""
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        results = User.objects.filter(role=User.Role.MOTHER).filter(
            Q(username__icontains=query) | Q(phone_number__icontains=query)
        )
    return render(request, "hospital_portal/dashboard.html", {"query": query, "results": results})


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

    return render(request, "hospital_portal/mother_detail.html", {
        "mother": mother,
        "profile": profile,
        "visits": visits,
        "checklist": _completeness_checklist(visits),
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