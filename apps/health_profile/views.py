from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import HealthProfile
from .forms import HealthProfileForm


@login_required
def health_profile_page(request):
    """GET/POST /health-profile/ -- view + edit your own health profile.
    Auto-creates the profile on first visit so there's never a 404."""
    profile, _ = HealthProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = HealthProfileForm(request.POST, instance=profile)
        if form.is_valid():
            dates_changed = bool(
                {"last_menstrual_period", "edd_is_manual_override"} & set(form.changed_data)
            )
            instance = form.save()
            if dates_changed:
                instance.recalculate_derived_dates()
            messages.success(request, "Health profile updated.")
            return redirect("health-profile")
    else:
        form = HealthProfileForm(instance=profile)

    return render(request, "health_profile/profile.html", {"form": form, "profile": profile})