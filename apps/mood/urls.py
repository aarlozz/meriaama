from django.urls import path
from .views import mood_checkin_page

urlpatterns = [
    path("", mood_checkin_page, name="mood-checkin"),
]