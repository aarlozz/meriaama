import json
from django.conf import settings
from groq import Groq
from functools import lru_cache


@lru_cache(maxsize=1)
def get_client():
    return Groq(api_key=settings.GROQ_API_KEY)


_client = get_client  # kept as an alias so any code written against the old private name still works


SYSTEM_PROMPT = """You are Meri Aama's wellness assistant. You give supportive,
evidence-based guidance to pregnant mothers using ONLY the retrieved source
excerpts provided to you.

Respond ONLY as JSON in this exact shape, nothing else:
{"summary": "1-2 sentence direct answer", "key_points": ["point 1", "point 2", ...]}

Rules:
- Base every claim on the provided sources; do not invent medical facts.
- If the sources don't cover the question, say so plainly in "summary" and
  leave key_points minimal -- do not fabricate an answer.
- Keep tone warm, simple, and non-alarming.
- Keep key_points short and scannable.
- NEVER include source names in the summary or key points.
- CRITICAL SAFETY RULE: the mother's known allergies and conditions are
  listed below. NEVER recommend a food, ingredient, or activity that
  conflicts with a listed allergy.
- Never provide an emergency diagnosis; direct urgent symptoms to a doctor
  or emergency services immediately.
"""


def build_prompt(user_query, retrieved_chunks, gestational_week=None, mood_score=None,
                  stress_level=None, allergies=None, has_gestational_diabetes=False,
                  has_hypertension=False, dietary_preference="none"):
    context_lines = []
    for i, chunk in enumerate(retrieved_chunks, start=1):
        context_lines.append(f"[Source {i}: {chunk['source_name']}] {chunk['text']}")
    context_block = "\n\n".join(context_lines) if context_lines else "No relevant sources found."

    safety_notes = []
    if allergies:
        safety_notes.append(f"Known allergies: {', '.join(allergies)}")
    if has_gestational_diabetes:
        safety_notes.append("Has gestational diabetes -- avoid recommending high-sugar foods without a caveat")
    if has_hypertension:
        safety_notes.append("Has hypertension -- avoid recommending high-sodium/salty foods without a caveat")
    if dietary_preference and dietary_preference != "none":
        safety_notes.append(f"Dietary preference: {dietary_preference}")
    safety_block = "\n".join(safety_notes) if safety_notes else "No known allergies or conditions on file."

    profile_line = f"Mother's context: gestational week {gestational_week}, mood score {mood_score}, stress level {stress_level}."

    return f"""{profile_line}

IMPORTANT -- safety information for this mother, must be respected in your answer:
{safety_block}

Retrieved sources:
{context_block}

Mother's question: {user_query}

Answer using only the sources above."""

def generate_recommendation(
    user_query,
    retrieved_chunks,
    gestational_week=None,
    mood_score=None,
    stress_level=None,
    allergies=None,
    has_gestational_diabetes=False,
    has_hypertension=False,
    dietary_preference="none",
):
    prompt = build_prompt(
        user_query,
        retrieved_chunks,
        gestational_week,
        mood_score,
        stress_level,
        allergies,
        has_gestational_diabetes,
        has_hypertension,
        dietary_preference,
    )

    response = get_client().chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=700,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "summary": raw,
            "key_points": [],
        }

    data.setdefault("summary", "")
    data.setdefault("key_points", [])

    # Build unique source list from retrieved chunks
    seen = set()
    sources = []

    for chunk in retrieved_chunks:
        name = chunk.get("source_name")
        url = chunk.get("source_url")

        if name and name not in seen:
            seen.add(name)
            sources.append({
                "name": name,
                "url": url,
            })

    data["sources_used"] = sources

    return data