"""
Usage:
    python manage.py seed_wellness_tips path/to/wellness_tips.json

Idempotent -- matches on each tip's unique "code", so re-running with an
updated file updates existing tips instead of duplicating them.
"""
import json
from django.core.management.base import BaseCommand, CommandError
from apps.daily_wellness.models import WellnessTip


class Command(BaseCommand):
    help = "Load/update WellnessTip rows from a JSON fixture file"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str)

    def handle(self, *args, **options):
        try:
            with open(options["json_path"], "r", encoding="utf-8") as f:
                tips = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {options['json_path']}")

        created = updated = 0
        for tip in tips:
            obj, was_created = WellnessTip.objects.update_or_create(
                code=tip["code"],
                defaults={
                    "category": tip["category"],
                    "trimester": tip["trimester"],
                    "text": tip["text"],
                    "avoid_if_allergic_to": tip.get("avoid_if_allergic_to", []),
                    "avoid_if_condition": tip.get("avoid_if_condition", []),
                    "avoid_if_diet": tip.get("avoid_if_diet", []),
                    "is_active": tip.get("is_active", True),
                    "only_if_condition": tip.get("only_if_condition", []),
                    "source_name": tip.get("source_name", ""),
                    "source_url": tip.get("source_url", ""),
                },
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created}, updated {updated}."))