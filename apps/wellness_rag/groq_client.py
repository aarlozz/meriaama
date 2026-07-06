from django.conf import settings
from groq import Groq
from functools import lru_cache


@lru_cache(maxsize=1)
def get_client():
    return Groq(api_key=settings.GROQ_API_KEY)


# kept as an alias so any code written against the old private name still works
_client = get_client


SYSTEM_PROMPT = """You are Meri Aama's wellness assistant. You give supportive,
evidence-based guidance to pregnant mothers using ONLY the retrieved source
excerpts provided to you. Rules:
- Base every claim on the provided sources; do not invent medical facts.
- If the sources don't cover the question, say so plainly and suggest the
  mother use the Doctor Chat feature instead.
- Keep tone warm, simple, and non-alarming.
- Never provide an emergency diagnosis; direct urgent symptoms to a doctor
  or emergency services immediately.
- At the end, list the sources you used by name.
"""


def build_prompt(user_query, retrieved_chunks, gestational_week=None, mood_score=None, stress_level=None):
    context_lines = []
    for i, chunk in enumerate(retrieved_chunks, start=1):
        context_lines.append(f"[Source {i}: {chunk['source_name']}] {chunk['text']}")
    context_block = "\n\n".join(context_lines) if context_lines else "No relevant sources found."

    profile_line = f"Mother's context: gestational week {gestational_week}, mood score {mood_score}, stress level {stress_level}."

    return f"""{profile_line}

Retrieved sources:
{context_block}

Mother's question: {user_query}

Answer the question using only the sources above, and list which sources you used."""


def generate_recommendation(user_query, retrieved_chunks, gestational_week=None, mood_score=None, stress_level=None):
    prompt = build_prompt(user_query, retrieved_chunks, gestational_week, mood_score, stress_level)
    response = _client().chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=600,
    )
    return response.choices[0].message.content
