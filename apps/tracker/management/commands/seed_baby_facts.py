"""
Usage:
    python manage.py seed_baby_facts baby_facts.json
    python manage.py seed_baby_facts baby_facts.json --dry-run
"""

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.tracker.models import WeeklyBabyFact

REQUIRED_KEYS = (
    "start_week",
    "end_week",
    "trimester",
    "title",
    "size_comparison",
    "baby_development",
)


class Command(BaseCommand):
    help = "Load or update WeeklyBabyFact records from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_path",
            type=str,
            help="Path to baby_facts.json",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the file and report what would happen, without writing to the database.",
        )

    def handle(self, *args, **options):
        json_path = options["json_path"]
        dry_run = options["dry_run"]

        try:
            with open(json_path, "r", encoding="utf-8-sig") as file:
                records = json.load(file)
        except FileNotFoundError:
            raise CommandError(f"File not found: {json_path}")
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON: {exc}")

        if not isinstance(records, list):
            raise CommandError("Top-level JSON must be a list of records.")

        created = 0
        updated = 0
        skipped = 0
        seen_ranges = {}  # (start_week, end_week) -> title, to catch dupes within the file itself

        for index, item in enumerate(records):

            if not isinstance(item, dict):
                self.stderr.write(
                    self.style.WARNING(f"Record {index}: not a JSON object, skipping.")
                )
                skipped += 1
                continue

            missing = [key for key in REQUIRED_KEYS if key not in item]

            if missing:
                self.stderr.write(
                    self.style.WARNING(
                        f"Record {index}: missing required field(s) {missing}, skipping."
                    )
                )
                skipped += 1
                continue

            start_week = item["start_week"]
            end_week = item["end_week"]

            if start_week > end_week:
                self.stderr.write(
                    self.style.WARNING(
                        f"Record {index}: start_week ({start_week}) is after "
                        f"end_week ({end_week}), skipping."
                    )
                )
                skipped += 1
                continue

            # Catch exact-duplicate ranges within the same JSON file.
            range_key = (start_week, end_week)
            if range_key in seen_ranges:
                self.stderr.write(
                    self.style.WARNING(
                        f"Record {index}: duplicate range {start_week}-{end_week} "
                        f"also used by '{seen_ranges[range_key]}', skipping."
                    )
                )
                skipped += 1
                continue
            seen_ranges[range_key] = item["title"]

            # Catch suspiciously wide ranges that would swallow many weeks
            # (e.g. a placeholder row like 1-40) -- these silently outrank
            # correct single-week rows in get_weekly_baby_fact() lookups.
            if (end_week - start_week) > 4:
                self.stderr.write(
                    self.style.WARNING(
                        f"Record {index}: range {start_week}-{end_week} spans "
                        f"{end_week - start_week + 1} weeks -- wider than expected, "
                        f"double check this isn't a placeholder row."
                    )
                )

            if dry_run:
                self.stdout.write(
                    f"Record {index}: would upsert weeks "
                    f"{start_week}-{end_week} ({item['title']})"
                )
                continue

            try:
                with transaction.atomic():
                    _, was_created = WeeklyBabyFact.objects.update_or_create(
                        start_week=start_week,
                        end_week=end_week,
                        defaults={
                            "trimester": item["trimester"],
                            "title": item["title"],
                            "size_comparison": item["size_comparison"],
                            "average_length_cm": item.get("average_length_cm"),
                            "average_weight_g": item.get("average_weight_g"),
                            "image_name": item.get("image_name", ""),
                            "baby_development": item["baby_development"],
                            "mother_changes": item.get("mother_changes", []),
                            "nutrition_tip": item.get("nutrition_tip", ""),
                            "exercise_tip": item.get("exercise_tip", ""),
                            "weekly_milestone": item.get("weekly_milestone", ""),
                            "fun_fact": item.get("fun_fact", ""),
                            "warning_signs": item.get("warning_signs", []),
                            "is_active": item.get("is_active", True),
                        },
                    )
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(f"Record {index}: failed to save ({exc}), skipping.")
                )
                skipped += 1
                continue

            if was_created:
                created += 1
            else:
                updated += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run complete.\n"
                    f"Valid records : {len(records) - skipped}\n"
                    f"Skipped       : {skipped}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Completed.\n"
                    f"Created : {created}\n"
                    f"Updated : {updated}\n"
                    f"Skipped : {skipped}"
                )
            )