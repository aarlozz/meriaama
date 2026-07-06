from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import MotherRegisterForm


def register_page(request):
    """GET/POST /register/ -- signup form for mothers."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = MotherRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # log the mother in immediately after signup
            return redirect("dashboard")
    else:
        form = MotherRegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    """GET /  -- landing page after login, links out to all 6 mother features."""
    profile = getattr(request.user, "health_profile", None)
    return render(request, "accounts/dashboard.html", {"profile": profile})