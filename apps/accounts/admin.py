from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class MeriAamaUserAdmin(UserAdmin):
    """
    Extends Django's built-in UserAdmin so hospital staff accounts
    (doctor/nurse/data_entry) can be created here with a role assigned.
    This IS the account-creation half of the Hospital Data Entry Portal.
    """
    fieldsets = UserAdmin.fieldsets + (
        ("Meri Aama role", {"fields": ("role", "phone_number", "preferred_language")}),
    )
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")