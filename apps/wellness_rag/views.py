from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Recommendation
from .forms import WellnessQueryForm
from .vector_store import query_knowledge, query_user_reports
from .groq_client import generate_recommendation


@login_required
def wellness_chat_page(request):
    """GET/POST /wellness/ -- ask a question, get a grounded answer, see history."""
    answer = None

    if request.method == "POST":
        form = WellnessQueryForm(request.POST)
        if form.is_valid():
            user_query = form.cleaned_data["query"]

            profile = getattr(request.user, "health_profile", None)
            gestational_week = getattr(profile, "current_gestational_week", None)
            mood_score = getattr(profile, "latest_mood_score", None)
            stress_level = getattr(profile, "latest_stress_level", None)

            retrieval_query = user_query
            if gestational_week:
                retrieval_query += f" (week {gestational_week} of pregnancy)"

            # Combine general knowledge with this mother's own report data --
            # personal chunks first, since her own numbers are most specific.
            personal_chunks = query_user_reports(retrieval_query, user_id=request.user.id, top_k=2)
            public_chunks = query_knowledge(retrieval_query, top_k=4)
            retrieved_chunks = personal_chunks + public_chunks

            answer = generate_recommendation(
                user_query=user_query,
                retrieved_chunks=retrieved_chunks,
                gestational_week=gestational_week,
                mood_score=mood_score,
                stress_level=stress_level,
            )

            Recommendation.objects.create(
                user=request.user,
                query=user_query,
                retrieved_sources=retrieved_chunks,
                response_text=answer,
            )
            form = WellnessQueryForm()  # clear the box after asking
    else:
        form = WellnessQueryForm()

    history = Recommendation.objects.filter(user=request.user)[:10]
    return render(request, "wellness/ask.html", {"form": form, "answer": answer, "history": history,"header_title": "Meri Aama AI",
"header_subtitle": "Get AI-powered guidance for your pregnancy"})