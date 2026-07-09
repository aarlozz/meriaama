from django.contrib import admin
from .models import TrimesterNarrativeCache


@admin.register(TrimesterNarrativeCache)
class TrimesterNarrativeCacheAdmin(admin.ModelAdmin):
    list_display = ("user", "visit_count_at_generation", "generated_at")