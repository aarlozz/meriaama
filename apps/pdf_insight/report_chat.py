import json
from django.conf import settings
from apps.wellness_rag.groq_client import get_client  # shared Groq client is fine to reuse
from .vector_store import query_report_chunks

ANSWER_SYSTEM_PROMPT = """You are a maternal health assistant helping a
mother understand her own uploaded medical report(s). You will be given
retrieved excerpts from her reports. Answer ONLY using the provided context.

If the context does not contain enough information to answer confidently,
say so plainly rather than guessing.

Do not diagnose. Do not recommend medication changes. Encourage her to
discuss anything concerning with her doctor.

Respond ONLY as JSON:
{"summary": "...", "key_points": ["...", "..."]}
"""


def ask_about_reports(user, question, top_k=5):
    hits = query_report_chunks(question, user.id, top_k=top_k)

    if not hits:
        return {
            "summary": "I couldn't find anything in your uploaded reports to answer "
                       "that. Try uploading the relevant report, or ask your doctor directly.",
            "key_points": [],
        }

    context_text = "\n\n".join(f"[Report excerpt] {hit['text']}" for hit in hits)

    response = get_client().chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nContext:\n{context_text}"},
        ],
        temperature=0.2,
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return {"summary": response.choices[0].message.content, "key_points": []}