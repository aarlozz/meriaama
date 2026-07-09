from django.contrib import admin
from .models import PrenatalVisit


@admin.register(PrenatalVisit)
class PrenatalVisitAdmin(admin.ModelAdmin):
    """
    Kept as a secondary/admin view of the same data for you (as the actual
    admin) to audit -- the real staff workflow is the custom pages under
    /hospital/, not this admin screen.
    """
    list_display = ("mother", "visit_date", "gestational_week", "entered_by")
    list_filter = ("gestational_week",)

from .models import PrenatalVisit, Medication

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ("mother", "name", "dosage", "start_date", "duration_days", "prescribed_by")    