from django.apps import AppConfig


class PregnancyDashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pregnancy_dashboard"  # adjust if your apps aren't under an `apps.` package
    verbose_name = "Pregnancy Dashboard"