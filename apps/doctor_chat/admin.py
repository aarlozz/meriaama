from django.contrib import admin
from .models import DoctorAssignment, ChatMessage


@admin.register(DoctorAssignment)
class DoctorAssignmentAdmin(admin.ModelAdmin):
    list_display = ("mother", "doctor", "is_active", "assigned_by", "assigned_at")
    list_filter = ("is_active",)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("assignment", "sender", "is_read", "created_at")