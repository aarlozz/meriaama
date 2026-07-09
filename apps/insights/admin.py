from django.contrib import admin
from .models import InsightSuggestion


@admin.register(InsightSuggestion)
class InsightSuggestionAdmin(admin.ModelAdmin):
    list_display = ("code", "condition", "severity", "is_active")
    list_filter = ("condition", "severity", "is_active")