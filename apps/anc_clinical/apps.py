from django.apps import AppConfig


class AncClinicalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.anc_clinical"

    def ready(self):
        import apps.anc_clinical.signals  # noqa: F401
