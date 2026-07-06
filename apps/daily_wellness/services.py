"""
Daily plan selection: trimester + allergy/condition/diet filtering happens
here, in plain Python, BEFORE anything is shown to the user or sent to an
LLM. The optional Groq step later only rephrases what already passed this
filter -- it is never allowed to introduce a new food or activity.
"""
import random
from datetime import date
from django.conf import settings
from .models import WellnessTip, DailyWellnessLog


def _trimester_bucket(gestational_week):
    if not gestational_week:
        return "second"  # sensible fallback if the profile isn't fully filled in yet
    if gestational_week <= 13:
        return "first"
    if gestational_week <= 27:
        return "second"
    return "third"


def _filter_safe(tips, allergies, conditions, diet_pref):
    allergy_set = set(allergies or [])
    condition_set = set(conditions or [])
    safe = []
    for tip in tips:
        if allergy_set & set(tip.avoid_if_allergic_to or []):
            continue
        if condition_set & set(tip.avoid_if_condition or []):
            continue
        if diet_pref and diet_pref != "none" and diet_pref in (tip.avoid_if_diet or []):
            continue
        safe.append(tip)
    return safe


def _pick_one(candidates, seed_key):
    if not candidates:
        return None
    return random.Random(seed_key).choice(candidates)


def build_daily_plan(user, profile, target_date=None):
    target_date = target_date or date.today()
    bucket = _trimester_bucket(profile.current_gestational_week)

    conditions = []
    if profile.has_gestational_diabetes:
        conditions.append("gestational_diabetes")
    if profile.has_hypertension:
        conditions.append("hypertension")

    picks = {}
    for category in WellnessTip.Category.values:
        candidates = list(WellnessTip.objects.filter(
            category=category, trimester__in=[bucket, WellnessTip.Trimester.ALL], is_active=True,
        ))
        safe_candidates = _filter_safe(candidates, profile.allergies, conditions, profile.dietary_preference)
        seed_key = f"{user.id}-{target_date.isoformat()}-{category}"  # stable per user per day
        picks[category] = _pick_one(safe_candidates, seed_key)
    return picks


def personalize_plan(profile, log):
    """
    Rephrase the already-selected, already-safety-filtered tips into one
    warm paragraph. Explicitly instructed not to add or remove any fact.
    If this fails for any reason, callers should just fall back to showing
    the raw tip text -- this step is a bonus, never a dependency.
    """
    from apps.wellness_rag.groq_client import get_client

    lines = []
    for label, tip in [
        ("Nutrition", log.nutrition_tip), ("Mental wellbeing", log.mental_health_tip),
        ("Movement", log.exercise_tip), ("Precaution", log.precaution_tip),
    ]:
        if tip:
            lines.append(f"- {label}: {tip.text}")
    if not lines:
        return ""

    system_prompt = (
        "You are a warm maternal health companion writing a short daily note "
        "for a pregnant mother. You are given a fixed list of already-approved "
        "tips. Rewrite them as ONE warm, encouraging paragraph addressed to her "
        "directly, under 120 words. STRICT RULES: do not add any new food, "
        "activity, or medical fact that is not already listed below. Do not "
        "remove any precaution that is present. Do not diagnose."
    )
    user_content = (
        f"Gestational week: {profile.current_gestational_week or 'unknown'}\n"
        f"Approved tips for today:\n" + "\n".join(lines)
    )
    response = get_client().chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
        temperature=0.4,
        max_tokens=220,
    )
    return response.choices[0].message.content.strip()


def get_or_create_daily_plan(user):
    profile = getattr(user, "health_profile", None)
    if not profile:
        return None

    today = date.today()
    log, created = DailyWellnessLog.objects.get_or_create(user=user, date=today)

    if created:
        picks = build_daily_plan(user, profile, today)
        log.nutrition_tip = picks.get("nutrition")
        log.mental_health_tip = picks.get("mental_health")
        log.exercise_tip = picks.get("exercise")
        log.precaution_tip = picks.get("precaution")
        log.save()

        try:
            log.personalized_text = personalize_plan(profile, log)
            log.save(update_fields=["personalized_text"])
        except Exception:
            pass  # raw tips below still render fine without the personalized note

    return log