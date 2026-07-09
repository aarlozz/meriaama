from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .services import get_or_create_daily_plan


@login_required
def daily_plan_page(request):
    """GET /daily-plan/ -- today's safety-filtered nutrition/mental-health/exercise tips."""
    profile = getattr(request.user, "health_profile", None)
    if not profile or not profile.current_gestational_week:
        messages.info(request, "Add your last menstrual period in your health profile first, so today's plan can match your stage of pregnancy.")
        return redirect("health-profile")

    plan = get_or_create_daily_plan(request.user)
    return render(request, "daily_wellness/plan.html", {"plan": plan, "header_title": "Daily Wellness", "header_subtitle": "Stay healthy with your personalized daily plan", })