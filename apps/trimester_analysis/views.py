import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from apps.hospital_portal.models import PrenatalVisit
from .analysis import build_full_analysis, generate_narrative_prompt
from .models import TrimesterNarrativeCache


@login_required
def trimester_analysis_page(request):
    visits = list(
        PrenatalVisit.objects.filter(mother=request.user).order_by("gestational_week", "visit_date")
    )
    profile = getattr(request.user, "health_profile", None)
    # mother=request.user lets build_full_analysis pull LabResult /
    # UltrasoundReport rows and the anc_clinical trimester checklist for her.
    analysis = build_full_analysis(visits, profile, mother=request.user)
    latest_visit = visits[-1] if visits else None

    narrative = None
    if visits:
        cache, _ = TrimesterNarrativeCache.objects.get_or_create(user=request.user)
        regenerate = cache.visit_count_at_generation != len(visits) or not cache.narrative_json

        if regenerate:
            try:
                system_prompt, user_prompt = generate_narrative_prompt(analysis["trimesters"])
                from apps.wellness_rag.groq_client import get_client
                from django.conf import settings

                response = get_client().chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.4,
                    max_tokens=600,
                    response_format={"type": "json_object"},
                )
                parsed = json.loads(response.choices[0].message.content)
                cache.narrative_json = parsed
                cache.visit_count_at_generation = len(visits)
                cache.save()
                narrative = parsed
            except Exception:
                narrative = cache.narrative_json
        else:
            narrative = cache.narrative_json

    context = {
        "has_any_data": bool(visits),
        "analysis": analysis,
        "overall": analysis["overall"],
        "progress": analysis["progress"],
        "trimesters": analysis["trimesters"],
        "charts": analysis["charts"],
        "timeline": analysis["timeline"],
        "latest_visit": latest_visit,
        "narrative": narrative,
        "header_title": "Trimester Analysis",
        "header_subtitle": "Review your pregnancy progress",
    }
    return render(request, "trimester_analysis/dashboard.html", context)