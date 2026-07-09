from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import MotherRegisterForm, StaffRegisterForm
from .models import User


def landing_page(request):
    """GET / -- public landing page with two login boxes (mother / hospital staff)."""
    if request.user.is_authenticated:
        if request.user.role == User.Role.MOTHER:
            return redirect("dashboard")
        return redirect("hospital-dashboard")
    return render(request, "accounts/landing.html")


def register_page(request):
    """GET/POST /register/ -- mother signup, auto-logged-in after."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = MotherRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = MotherRegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    """GET /dashboard/ -- mother's informative home page: pregnancy progress,
    recent mood/stress signals, next visit reminder, and any flags worth
    her attention. Pulls from every app defensively so this page never
    crashes if one of them isn't installed yet."""
    profile = getattr(request.user, "health_profile", None)

    week = getattr(profile, "current_gestational_week", None)
    week_pct = min(round((week / 40) * 100), 100) if week else 0
    days_until_due = None
    due_date = getattr(profile, "expected_delivery_date", None)
    if due_date:
        from datetime import date
        days_until_due = (due_date - date.today()).days

    trimester = None
    if week:
        if week <= 13:
            trimester = 1
        elif week <= 27:
            trimester = 2
        else:
            trimester = 3

    recent_moods = []
    try:
        from apps.mood.models import MoodEntry
        recent_moods = list(MoodEntry.objects.filter(user=request.user)[:7])
    except Exception:
        pass

    latest_test = None
    try:
        from apps.psychometric.models import PsychometricTest
        latest_test = PsychometricTest.objects.filter(user=request.user).order_by("-taken_at").first()
    except Exception:
        pass

    next_visit_date = None
    active_flags = []
    try:
        from apps.hospital_portal.models import PrenatalVisit
        from apps.trimester_analysis.analysis import build_full_analysis
        from datetime import date

        visits = list(PrenatalVisit.objects.filter(mother=request.user))
        upcoming = [v.next_visit_date for v in visits if v.next_visit_date and v.next_visit_date >= date.today()]
        next_visit_date = min(upcoming) if upcoming else None

        for result in build_full_analysis(visits):
            for flag in result["flags"]:
                if flag["severity"] in ("concern", "caution"):
                    active_flags.append(flag)
    except Exception:
        pass

    return render(request, "accounts/dashboard.html", {
        "profile": profile,
        "week": week,
        "week_pct": week_pct,
        "days_until_due": days_until_due,
        "trimester": trimester,
        "recent_moods": recent_moods,
        "latest_test": latest_test,
        "next_visit_date": next_visit_date,
        "active_flags": active_flags[:3],
    })


def staff_login_page(request):
    """
    GET/POST /staff/login/ -- manual credential check (not Django's built-in
    LoginView) because authenticate() silently rejects inactive users before
    we ever get a chance to show a helpful "pending approval" message.
    """
    if request.user.is_authenticated:
        return redirect("hospital-dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        try:
            candidate = User.objects.get(username=username)
        except User.DoesNotExist:
            candidate = None

        if candidate is None or not candidate.check_password(password):
            messages.error(request, "Incorrect username or password.")
        elif not (candidate.is_hospital_staff() or candidate.is_hospital_admin()):
            messages.error(request, "This login is for hospital staff. Please use the mother login instead.")
        elif not candidate.is_active:
            messages.error(request, "Your account is pending admin approval. You'll be notified once approved.")
        else:
            login(request, candidate, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("hospital-dashboard")

    return render(request, "accounts/staff_login.html")


def staff_register_page(request):
    """GET/POST /staff/register/ -- creates an INACTIVE staff account, pending admin approval."""
    if request.user.is_authenticated:
        return redirect("hospital-dashboard")

    if request.method == "POST":
        form = StaffRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration submitted. An admin will review and approve your account before you can log in.")
            return redirect("staff-login")
    else:
        form = StaffRegisterForm()

    return render(request, "accounts/staff_register.html", {"form": form})