from django.urls import path
from .views import weekly_tracker_page

urlpatterns = [
    path("", weekly_tracker_page, name="weekly-tracker"),
]