from django.contrib import admin
from .models import WellnessTip, DailyWellnessLog


@admin.register(WellnessTip)
class WellnessTipAdmin(admin.ModelAdmin):
    list_display = ("code", "category", "trimester", "is_active")
    list_filter = ("category", "trimester", "is_active")
    search_fields = ("code", "text")


@admin.register(DailyWellnessLog)
class DailyWellnessLogAdmin(admin.ModelAdmin):
    list_display = ("user", "date")
    list_filter = ("date",)