"""
IMPORTANT: adjust the `dependencies` tuple below to point at YOUR actual
latest hospital_portal migration (run `python manage.py showmigrations
hospital_portal` to see the current head, then swap "0001_initial" for it
if your head is something else, e.g. "0003_something").

This migration only ADDS fields -- it does not touch or drop anything
existing, so it's safe to run on a database that already has PrenatalVisit
rows in it. Every new BooleanField defaults to False and every new
numeric/JSON field is null/blank-safe, so existing rows don't need backfill.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hospital_portal", "0004_medication_food_instruction_and_more"),  # <-- change if your head migration differs
    ]

    operations = [
        migrations.AddField(
            model_name="prenatalvisit",
            name="bp_systolic",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="prenatalvisit",
            name="bp_diastolic",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="prenatalvisit",
            name="pulse_bpm",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="prenatalvisit",
            name="spo2_percent",
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name="prenatalvisit",
            name="lungs_abnormal",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="prenatalvisit",
            name="heart_abnormal",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="prenatalvisit",
            name="pallor_present",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="prenatalvisit",
            name="jaundice_present",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="prenatalvisit",
            name="is_flagged",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="prenatalvisit",
            name="flag_reasons",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
