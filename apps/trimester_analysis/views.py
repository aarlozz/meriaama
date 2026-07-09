from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .analysis import generate_narrative_prompt

from .analysis import (
    build_full_analysis,
    generate_narrative_prompt,
)

from .models import TrimesterNarrativeCache


@login_required
def trimester_analysis_page(request):
    """
    Pregnancy dashboard showing

    - Overall summary
    - AI narrative
    - Visit timeline
    - Trimester analysis
    - Charts
    """

    try:
        from apps.hospital_portal.models import PrenatalVisit

        visits = list(
            PrenatalVisit.objects.filter(
                mother=request.user
            ).order_by("gestational_week", "visit_date")
        )

    except Exception:
        visits = []

    analysis = build_full_analysis(visits)

    latest_visit = visits[-1] if visits else None

    summary = {
        "total_visits": len(visits),
        "current_week": getattr(
            latest_visit,
            "gestational_week",
            None,
        ),
        "latest_weight": getattr(
            latest_visit,
            "maternal_weight_kg",
            None,
        ),
        "latest_bp": getattr(
            latest_visit,
            "blood_pressure",
            "",
        ),
        "latest_hb": getattr(
            latest_visit,
            "hemoglobin_g_dl",
            None,
        ),
        "latest_fhr": getattr(
            latest_visit,
            "fetal_heart_rate_bpm",
            None,
        ),
        "latest_fundal_height": getattr(
            latest_visit,
            "fundal_height_cm",
            None,
        ),
        "latest_position": getattr(
            latest_visit,
            "get_fetal_position_display",
            lambda: ""
        )(),
        "latest_edema": getattr(
            latest_visit,
            "get_edema_display",
            lambda: ""
        )(),
    }

    charts = {
        "weeks": [],
        "weight": [],
        "hb": [],
        "fundal": [],
        "fhr": [],
        "bp_sys": [],
        "bp_dia": [],
    }

    for visit in visits:

        if visit.gestational_week is None:
            continue

        charts["weeks"].append(
            visit.gestational_week
        )

        charts["weight"].append(
            float(visit.maternal_weight_kg)
            if visit.maternal_weight_kg is not None
            else None
        )

        charts["hb"].append(
            float(visit.hemoglobin_g_dl)
            if visit.hemoglobin_g_dl is not None
            else None
        )

        charts["fundal"].append(
            float(visit.fundal_height_cm)
            if visit.fundal_height_cm is not None
            else None
        )

        charts["fhr"].append(
            visit.fetal_heart_rate_bpm
        )

        if visit.blood_pressure:

            try:
                s, d = visit.blood_pressure.split("/")

                charts["bp_sys"].append(int(s))
                charts["bp_dia"].append(int(d))

            except Exception:

                charts["bp_sys"].append(None)
                charts["bp_dia"].append(None)

        else:

            charts["bp_sys"].append(None)
            charts["bp_dia"].append(None)

    narrative = ""

    if visits:

        cache, _ = TrimesterNarrativeCache.objects.get_or_create(
            user=request.user
        )

        regenerate = (
            cache.visit_count_at_generation != len(visits)
            or
            not cache.narrative_text
        )

        if regenerate:

            try:

                narrative = generate_narrative_prompt(
                    analysis
                )

                cache.visit_count_at_generation = len(visits)
                cache.narrative_text = narrative
                cache.save()

            except Exception:

                narrative = cache.narrative_text

        else:

            narrative = cache.narrative_text

    context = {

        "has_any_data": bool(visits),

        "summary": summary,

        "latest_visit": latest_visit,

        "timeline": visits,

        "trimester_results": analysis,

        "charts": charts,

        "narrative": narrative,
        "header_title": "Trimester Analysis",
"header_subtitle": "Review your progress across each trimester",
    }

    return render(
        request,
        "trimester_analysis/dashboard.html",
        context,
        
    )