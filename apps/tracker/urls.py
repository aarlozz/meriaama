from django.urls import path
from .views import tracker_page, mark_dose_taken

urlpatterns = [
    path("", tracker_page, name="tracker"),
    path("medication/<int:medication_id>/mark-taken/", mark_dose_taken, name="mark-dose-taken"),
]