from django.contrib import admin
from .models import HealthProfile


@admin.register(HealthProfile)
class HealthProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "current_gestational_week", "latest_mood_score", "latest_stress_level")
    search_fields = ("user__username",)
