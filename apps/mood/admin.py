from django.contrib import admin
from .models import MoodEntry


@admin.register(MoodEntry)
class MoodEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "score", "logged_at")