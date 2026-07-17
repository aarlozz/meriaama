"""
IMPORTANT: adjust `dependencies` below to point at YOUR actual latest
health_profile migration (run `python manage.py showmigrations health_profile`
-- note the app label is `health_profile`, taken from the folder name
apps/health_profile/, not the full dotted path).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("health_profile", "0001_initial"),  # <-- change if your head migration differs
    ]

    operations = [
        migrations.AddField(
            model_name="healthprofile",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
    ]
