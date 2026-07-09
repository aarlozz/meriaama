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
    """GET /dashboard/ -- mother's landing page after login."""
    profile = getattr(request.user, "health_profile", None)
    return render(request, "accounts/dashboard.html", {"profile": profile})


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