from django.contrib import admin
from .models import MedicalReport


@admin.register(MedicalReport)
class MedicalReportAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "uploaded_at")
    list_filter = ("status",)
    search_fields = ("user__username",)