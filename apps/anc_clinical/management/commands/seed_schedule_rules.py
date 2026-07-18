from django.core.management.base import BaseCommand
from apps.anc_clinical.models import AncScheduleRule
from apps.anc_clinical.reference_data import SCHEDULE_RULE_SEED


class Command(BaseCommand):
    help = "Seed AncScheduleRule from SCHEDULE_RULE_SEED (idempotent)."

    def handle(self, *args, **options):
        created_count = 0
        for row in SCHEDULE_RULE_SEED:
            key = {"category": row["category"], "code": row["code"]}
            if row["category"] == "lab":
                key["applies_to"] = row["applies_to"]
            else:
                key["week_min"] = row["week_min"]
            _, created = AncScheduleRule.objects.get_or_create(defaults=row, **key)
            if created:
                created_count += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created_count} new AncScheduleRule rows."))