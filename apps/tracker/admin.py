from django.contrib import admin
from .models import PersonalCheckIn, MedicationLog


@admin.register(PersonalCheckIn)
class PersonalCheckInAdmin(admin.ModelAdmin):
    list_display = ("user", "logged_at")


@admin.register(MedicationLog)
class MedicationLogAdmin(admin.ModelAdmin):
    list_display = ("medication", "date")