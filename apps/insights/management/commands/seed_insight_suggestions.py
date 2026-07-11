"""
Usage: python manage.py seed_insight_suggestions insight_suggestions.json
Idempotent -- matches on "code", same pattern as seed_wellness_tips.
Entries missing "code", "condition", "title", or "message" are skipped and
logged rather than crashing the whole command (and the rest of build.sh
along with it).
"""
import json
from django.core.management.base import BaseCommand, CommandError
from apps.insights.models import InsightSuggestion


class Command(BaseCommand):
    help = "Load/update InsightSuggestion rows from a JSON fixture file"

    REQUIRED_FIELDS = ["code", "condition", "title", "message"]

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str)

    def handle(self, *args, **options):
        try:
            with open(options["json_path"], "r", encoding="utf-8") as f:
                items = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {options['json_path']}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in {options['json_path']}: {e}")

        created = updated = skipped = 0

        for i, item in enumerate(items):
            missing = [field for field in self.REQUIRED_FIELDS if not item.get(field)]
            if missing:
                self.stdout.write(self.style.WARNING(
                    f"Skipping item at index {i} -- missing required field(s): {', '.join(missing)}"
                ))
                skipped += 1
                continue

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

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created {created}, updated {updated}, skipped {skipped}."
        ))
        if skipped:
            self.stdout.write(self.style.WARNING(
                f"{skipped} item(s) were skipped -- check insight_suggestions.json for missing fields."
            ))