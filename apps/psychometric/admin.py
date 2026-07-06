from django.contrib import admin
from .models import PsychometricTest


@admin.register(PsychometricTest)
class PsychometricTestAdmin(admin.ModelAdmin):
    list_display = ("user", "test_type", "total_score", "risk_level", "taken_at")
    list_filter = ("test_type", "risk_level")