"""
Extract text from an uploaded PDF with pdfplumber, then ask Groq to
summarize in plain language and flag abnormal values.
"""
import json
import pdfplumber
from apps.wellness_rag.groq_client import get_client
from django.conf import settings

SUMMARY_SYSTEM_PROMPT = """You are a medical report explainer for expecting
mothers. Given raw text extracted from a lab report, produce:
1. A short, plain-language summary (3-5 sentences, no jargon).
2. A list of any values that appear abnormal or outside typical reference
   ranges, each with the test name, value, and a one-line plain-language note.
Respond ONLY as JSON: {"summary": "...", "flagged_values": [{"test": "...", "value": "...", "note": "..."}]}
Do not diagnose. Do not recommend specific treatment. Encourage the mother
to discuss results with her doctor."""


def extract_text_from_pdf(file_path):
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def summarize_report(file_path):
    raw_text = extract_text_from_pdf(file_path)
    if not raw_text.strip():
        return {"summary": "Could not extract readable text from this PDF.", "flagged_values": []}

    response = get_client().chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": raw_text[:8000]},
        ],
        temperature=0.2,
        max_tokens=600,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return {"summary": response.choices[0].message.content, "flagged_values": []}