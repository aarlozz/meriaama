from django.contrib import admin
from .models import PersonalCheckIn, MedicationLog, DoctorQuestion, WeeklyBabyFact


@admin.register(PersonalCheckIn)
class PersonalCheckInAdmin(admin.ModelAdmin):
    list_display = ("user", "logged_at")


@admin.register(MedicationLog)
class MedicationLogAdmin(admin.ModelAdmin):
    list_display = ("medication", "date")


@admin.register(DoctorQuestion)
class DoctorQuestionAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "is_answered")


@admin.register(WeeklyBabyFact)
class WeeklyBabyFactAdmin(admin.ModelAdmin):
    list_display = ("start_week", "end_week", "size_comparison", "is_active")