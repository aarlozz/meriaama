from django.contrib import admin
from .models import WeeklyUpdate


@admin.register(WeeklyUpdate)
class WeeklyUpdateAdmin(admin.ModelAdmin):
    list_display = ("user", "gestational_week", "maternal_weight_kg", "blood_pressure", "updated_at")
    list_filter = ("gestational_week",)
    search_fields = ("user__username",)
    ordering = ("user", "gestational_week")