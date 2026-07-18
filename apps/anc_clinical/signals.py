"""
anc_clinical/signals.py

Three jobs, all signal-driven so hospital_portal and accounts stay
unaware that anc_clinical exists (no reverse imports):

1. Before a PrenatalVisit saves: parse `blood_pressure` ("120/80") into
   bp_systolic/bp_diastolic so the flag engine and any future numeric BP
   graphs don't have to re-parse the string. Staff still only type into
   `blood_pressure` -- nothing changes for them.

2. After a PrenatalVisit saves: run the flag engine and write
   is_flagged/flag_reasons back via a queryset .update() (NOT instance.save(),
   which would re-trigger this signal). Only writes if something changed,
   so a no-op re-save doesn't cost a write.

3. After a HealthProfile saves with an LMP set: generate the standard ANC
   visit schedule and medication care plan, per your corrected tables.
   Idempotent via get_or_create, so re-saving the profile (e.g. editing
   blood_group later) never creates duplicates.
"""
from datetime import timedelta

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.hospital_portal.models import PrenatalVisit
from apps.health_profile.models import HealthProfile


# ---------------------------------------------------------------------------
# 1 & 2. PrenatalVisit -- BP parsing + flagging
# ---------------------------------------------------------------------------
@receiver(pre_save, sender=PrenatalVisit)
def parse_blood_pressure(sender, instance, **kwargs):
    instance.bp_systolic = None
    instance.bp_diastolic = None
    if instance.blood_pressure and "/" in instance.blood_pressure:
        sys_str, _, dia_str = instance.blood_pressure.partition("/")
        try:
            instance.bp_systolic = int(sys_str.strip())
            instance.bp_diastolic = int(dia_str.strip())
        except ValueError:
            pass  # malformed entry (e.g. "120-80") -- leave both null, don't crash the save


@receiver(post_save, sender=PrenatalVisit)
def flag_visit(sender, instance, **kwargs):
    from .flag_engine import evaluate_visit

    is_flagged, flag_reasons = evaluate_visit(instance)
    if instance.is_flagged != is_flagged or instance.flag_reasons != flag_reasons:
        PrenatalVisit.objects.filter(pk=instance.pk).update(
            is_flagged=is_flagged, flag_reasons=flag_reasons
        )
        # keep the in-memory instance consistent for the current request
        # (e.g. if the view re-renders `instance` right after saving)
        instance.is_flagged = is_flagged
        instance.flag_reasons = flag_reasons


# ---------------------------------------------------------------------------
# 3. HealthProfile -- auto-generate visit schedule + medication care plan
# ---------------------------------------------------------------------------
def _generate_visit_schedule(profile):
    """
    Standard tertiary-hospital ANC schedule:
      up to 28 wks   -> every 4 weeks
      28-36 wks      -> every 2 weeks
      36 wks-delivery-> every 7 days
    Starts from booking (~8 weeks) or the mother's current gestational
    week, whichever is later, and stops at week 40. Only future dates are
    written (past ones would just show as permanently "missed" clutter).
    """
    from .models import VisitSchedule
    from django.utils import timezone

    if not profile.last_menstrual_period:
        return

    lmp = profile.last_menstrual_period
    today = timezone.localdate()
    start_week = max(profile.current_gestational_week or 8, 8)

    week = start_week
    while week <= 40:
        expected_date = lmp + timedelta(weeks=week)
        if expected_date >= today:
            VisitSchedule.objects.get_or_create(
                mother=profile.user,
                expected_gestational_week=week,
                defaults={"expected_date": expected_date},
            )
        if week < 28:
            week += 4
        elif week < 36:
            week += 2
        else:
            week += 1


def _generate_medication_plan(profile):
    """
    Auto-generated starter care plan per your corrected timing table.
    prescribed_by=None marks these as system-generated (vs. a doctor's own
    prescription) -- filter on that in the UI if you want to visually
    distinguish them. All are idempotent via get_or_create on
    (mother, name) so repeated profile saves don't duplicate them.
    """
    from apps.hospital_portal.models import Medication

    if not profile.last_menstrual_period or not profile.expected_delivery_date:
        return

    lmp = profile.last_menstrual_period
    edd = profile.expected_delivery_date
    today_span = (edd - lmp).days

    def days_from_lmp(weeks):
        return lmp + timedelta(weeks=weeks)

    plan = [
        dict(
            name="Iron + Folic Acid", dosage="1 tablet", medication_type="supplement",
            purpose="Routine antenatal supplementation", route="oral",
            frequency_per_day=1, medicine_time="morning", food_instruction="after",
            start_date=lmp, duration_days=today_span,
        ),
        dict(
            name="Calcium", dosage="500 mg", medication_type="supplement",
            purpose="Routine antenatal supplementation (from ~14-20 wks)", route="oral",
            frequency_per_day=2, medicine_time="evening", food_instruction="after",
            start_date=days_from_lmp(14), duration_days=max(today_span - 14 * 7, 1),
        ),
        dict(
            name="Tetanus Toxoid (TT1)", dosage="0.5 mL IM", medication_type="other",
            purpose="Tetanus prophylaxis - 1st dose", route="injection",
            frequency_per_day=1, medicine_time="morning", food_instruction="any",
            start_date=days_from_lmp(14), duration_days=1,
        ),
        dict(
            name="Tetanus Toxoid (TT2)", dosage="0.5 mL IM", medication_type="other",
            purpose="Tetanus prophylaxis - 2nd dose (4 wks after TT1, before 36 wks)", route="injection",
            frequency_per_day=1, medicine_time="morning", food_instruction="any",
            start_date=min(days_from_lmp(18), days_from_lmp(36)), duration_days=1,
        ),
        dict(
            name="Albendazole (Deworming)", dosage="400 mg", medication_type="other",
            purpose="Deworming - once in 2nd trimester", route="oral",
            frequency_per_day=1, medicine_time="morning", food_instruction="after",
            start_date=days_from_lmp(20), duration_days=1,
        ),
    ]

    if profile.blood_group and profile.blood_group.strip().endswith("-"):
        plan.append(dict(
            name="Anti-D Immunoglobulin", dosage="300 mcg IM", medication_type="other",
            purpose="Rh-negative mother - isoimmunization prophylaxis", route="injection",
            frequency_per_day=1, medicine_time="morning", food_instruction="any",
            start_date=days_from_lmp(28), duration_days=1,
        ))

    for item in plan:
        Medication.objects.get_or_create(
            mother=profile.user,
            name=item["name"],
            defaults={**item, "prescribed_by": None, "notes": "Auto-generated standard ANC care plan"},
        )


@receiver(post_save, sender=HealthProfile)
def generate_care_plan_and_schedule(sender, instance, **kwargs):
    if not instance.last_menstrual_period:
        return
    _generate_visit_schedule(instance)
    _generate_medication_plan(instance)
