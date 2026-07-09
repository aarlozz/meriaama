"""
Usage: python manage.py seed_insight_suggestions insight_suggestions.json
Idempotent -- matches on "code", same pattern as seed_wellness_tips.
"""
import json
from django.core.management.base import BaseCommand, CommandError
from apps.insights.models import InsightSuggestion


class Command(BaseCommand):
    help = "Load/update InsightSuggestion rows from a JSON fixture file"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str)

    def handle(self, *args, **options):
        try:
            with open(options["json_path"], "r", encoding="utf-8") as f:
                items = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {options['json_path']}")

        created = updated = 0
        for item in items:
            obj, was_created = InsightSuggestion.objects.update_or_create(
                code=item["code"],
                defaults={
                    "condition": item["condition"],
                    "severity": item.get("severity", "info"),
                    "title": item["title"],
                    "message": item["message"],
                    "action_target": item.get("action_target", ""),
                    "action_label": item.get("action_label", ""),
                    "is_active": item.get("is_active", True),
                },
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created}, updated {updated}."))