from django.contrib import admin
from .models import ClinicalRecord


@admin.register(ClinicalRecord)
class ClinicalRecordAdmin(admin.ModelAdmin):
    """
    This *is* the Hospital Data Entry Portal for the prototype -- Django's
    built-in admin, restricted to hospital-role staff. Give doctor/nurse/
    data_entry users `is_staff=True` (via the accounts admin) plus the
    permissions below so they can only touch this model, not the whole site.
    """
    list_display = ("mother", "gestational_week", "entered_by", "recorded_at")
    list_filter = ("gestational_week",)
    autocomplete_fields = ["mother"]

    def save_model(self, request, obj, form, change):
        if not obj.entered_by_id:
            obj.entered_by = request.user
        super().save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return request.user.is_superuser or getattr(request.user, "is_hospital_staff", lambda: False)()
