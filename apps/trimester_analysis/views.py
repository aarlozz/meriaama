from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .analysis import build_full_analysis


@login_required
def trimester_analysis_page(request):
    """GET /trimester-analysis/ -- weight/BP/other trends and flags, grouped by trimester."""
    try:
        from apps.hospital_portal.models import PrenatalVisit
        visits = list(PrenatalVisit.objects.filter(mother=request.user))
    except Exception:
        visits = []

    trimester_results = build_full_analysis(visits)

    return render(request, "trimester_analysis/dashboard.html", {
        "trimester_results": trimester_results,
        "has_any_data": bool(visits),
    })