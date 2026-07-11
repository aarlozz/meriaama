from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Recommendation
from .forms import WellnessQueryForm
from .vector_store import query_knowledge, query_user_reports
from .groq_client import generate_recommendation
from .safety import check_allergen_mentions


@login_required
def wellness_chat_page(request):
    """GET/POST /wellness/ -- ask a question, get a grounded + allergy-checked answer, see history."""
    answer = None
    answer_flags = []

    if request.method == "POST":
        form = WellnessQueryForm(request.POST)
        if form.is_valid():
            user_query = form.cleaned_data["query"]

            profile = getattr(request.user, "health_profile", None)
            gestational_week = getattr(profile, "current_gestational_week", None)
            mood_score = getattr(profile, "latest_mood_score", None)
            stress_level = getattr(profile, "latest_stress_level", None)
            allergies = getattr(profile, "allergies", []) or []
            has_gestational_diabetes = getattr(profile, "has_gestational_diabetes", False)
            has_hypertension = getattr(profile, "has_hypertension", False)
            dietary_preference = getattr(profile, "dietary_preference", "none")

            retrieval_query = user_query
            if gestational_week:
                retrieval_query += f" (week {gestational_week} of pregnancy)"

            personal_chunks = query_user_reports(retrieval_query, user_id=request.user.id, top_k=2)
            public_chunks = query_knowledge(retrieval_query, top_k=4)
            retrieved_chunks = personal_chunks + public_chunks

            structured_answer = generate_recommendation(
                user_query=user_query,
                retrieved_chunks=retrieved_chunks,
                gestational_week=gestational_week,
                mood_score=mood_score,
                stress_level=stress_level,
                allergies=allergies,
                has_gestational_diabetes=has_gestational_diabetes,
                has_hypertension=has_hypertension,
                dietary_preference=dietary_preference,
            )

            full_text = structured_answer.get("summary", "") + " " + " ".join(structured_answer.get("key_points", []))
            safety_flags = check_allergen_mentions(full_text, allergies)

            Recommendation.objects.create(
                user=request.user,
                query=user_query,
                retrieved_sources=retrieved_chunks,
                response_text=structured_answer.get("summary", ""),
                structured_response=structured_answer,
                safety_flags=safety_flags,
            )

            answer = structured_answer
            answer_flags = safety_flags
            form = WellnessQueryForm()  # clear the box after asking
    else:
        form = WellnessQueryForm()

    history = Recommendation.objects.filter(user=request.user)[:10]
    return render(request, "wellness/ask.html", {
        "form": form, "answer": answer, "answer_flags": answer_flags, "history": history,
        "header_title": "Meri Aama AI",
        "header_subtitle": "Get AI-powered guidance for your pregnancy",
    })