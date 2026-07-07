from django.contrib import admin
from .models import PersonalCheckIn


@admin.register(PersonalCheckIn)
class PersonalCheckInAdmin(admin.ModelAdmin):
    list_display = ("user", "visit_date", "gestational_week")