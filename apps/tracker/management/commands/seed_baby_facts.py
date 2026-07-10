"""Usage: python manage.py seed_baby_facts baby_facts.json"""
import json
from django.core.management.base import BaseCommand, CommandError
from apps.tracker.models import WeeklyBabyFact


class Command(BaseCommand):
    help = "Load/update WeeklyBabyFact rows from a JSON fixture file"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str)

    def handle(self, *args, **options):
        try:
            with open(options["json_path"], "r", encoding="utf-8-sig") as f:
                items = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {options['json_path']}")

        created = updated = 0
        for item in items:
            obj, was_created = WeeklyBabyFact.objects.update_or_create(
                start_week=item["start_week"],
                end_week=item["end_week"],
                defaults={
                    "size_comparison": item.get("size_comparison", ""),
                    "fact_text": item["fact_text"],
                    "is_active": item.get("is_active", True),
                },
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created}, updated {updated}."))