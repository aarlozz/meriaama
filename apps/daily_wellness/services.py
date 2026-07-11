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
        return "second"

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

        if (
            diet_pref
            and diet_pref != "none"
            and diet_pref in (tip.avoid_if_diet or [])
        ):
            continue

        if (
            tip.only_if_condition
            and not (condition_set & set(tip.only_if_condition))
        ):
            continue

        safe.append(tip)

    return safe


def _pick_multiple(candidates, seed_key, n=3):
    """
    Stable per-user-per-day random selection.
    """

    if not candidates:
        return []

    rng = random.Random(seed_key)

    if len(candidates) <= n:
        picked = candidates[:]
        rng.shuffle(picked)
        return picked

    return rng.sample(candidates, n)


def build_daily_plan(
    user,
    profile,
    target_date=None,
    tips_per_category=3,
):
    target_date = target_date or date.today()

    bucket = _trimester_bucket(profile.current_gestational_week)

    conditions = []

    if profile.has_gestational_diabetes:
        conditions.append("gestational_diabetes")

    if profile.has_hypertension:
        conditions.append("hypertension")

    print("=" * 60)
    print("Generating Daily Wellness Plan")
    print("Week:", profile.current_gestational_week)
    print("Trimester:", bucket)
    print("Allergies:", profile.allergies)
    print("Conditions:", conditions)
    print("Diet:", profile.dietary_preference)

    picks = {}

    for category in WellnessTip.Category.values:

        candidates = list(
            WellnessTip.objects.filter(
                category=category,
                trimester__in=[
                    bucket,
                    WellnessTip.Trimester.ALL,
                ],
                is_active=True,
            )
        )

        print("\nCATEGORY:", category)
        print("Candidates:", len(candidates))

        safe_candidates = _filter_safe(
            candidates,
            profile.allergies,
            conditions,
            profile.dietary_preference,
        )

        print("Safe candidates:", len(safe_candidates))

        seed_key = (
            f"{user.id}-"
            f"{target_date.isoformat()}-"
            f"{category}"
        )

        selected = _pick_multiple(
            safe_candidates,
            seed_key,
            n=tips_per_category,
        )

        print("Selected:", len(selected))

        picks[category] = selected

    return picks

def personalize_plan(profile, log):
    """
    Rephrase the already-selected, already-safety-filtered tips into one
    warm paragraph.

    The AI NEVER creates new advice—it only rewrites the already-approved
    recommendations.
    """

    from apps.wellness_rag.groq_client import get_client

    lines = []

    for label, tips in [
        ("Nutrition", log.nutrition_tips.all()),
        ("Mental wellbeing", log.mental_health_tips.all()),
        ("Movement", log.exercise_tips.all()),
        ("Precaution", log.precaution_tips.all()),
    ]:
        for tip in tips:
            lines.append(f"- {label}: {tip.text}")

    if not lines:
        return ""

    system_prompt = (
        "You are a warm maternal health companion writing a short daily note "
        "for a pregnant mother. You are given a fixed list of already-approved "
        "tips. Rewrite them as ONE encouraging paragraph addressed directly "
        "to her. Keep it under 150 words. "
        "Never introduce new foods, exercises, medicines, or medical facts. "
        "Do not remove any precaution. "
        "Do not diagnose."
    )

    user_prompt = (
        f"Gestational week: {profile.current_gestational_week or 'unknown'}\n\n"
        f"Approved tips:\n"
        + "\n".join(lines)
    )

    response = get_client().chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.4,
        max_tokens=260,
    )

    return response.choices[0].message.content.strip()


def get_or_create_daily_plan(user):
    """
    Returns today's cached wellness plan.

    If today's plan doesn't exist OR is empty,
    regenerate it automatically.
    """

    profile = getattr(user, "health_profile", None)

    if not profile:
        return None

    today = date.today()

    log, created = DailyWellnessLog.objects.get_or_create(
        user=user,
        date=today,
    )

    regenerate = (
        created
        or log.nutrition_tips.count() == 0
        or log.mental_health_tips.count() == 0
        or log.exercise_tips.count() == 0
        or log.precaution_tips.count() == 0
    )

    if regenerate:

        print("=" * 70)
        print("Generating Daily Wellness Recommendations...")

        picks = build_daily_plan(
            user=user,
            profile=profile,
            target_date=today,
            tips_per_category=3,
        )

        print("Nutrition:", len(picks["nutrition"]))
        print("Mental:", len(picks["mental_health"]))
        print("Exercise:", len(picks["exercise"]))
        print("Precaution:", len(picks["precaution"]))

        log.save()

        log.nutrition_tips.set(
            picks.get("nutrition", [])
        )

        log.mental_health_tips.set(
            picks.get("mental_health", [])
        )

        log.exercise_tips.set(
            picks.get("exercise", [])
        )

        log.precaution_tips.set(
            picks.get("precaution", [])
        )

        try:
            log.personalized_text = personalize_plan(
                profile,
                log,
            )

            log.save(update_fields=["personalized_text"])

        except Exception as e:
            print("Groq personalization skipped:", e)

    return log