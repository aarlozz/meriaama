from django.urls import path
from .views import (
    tracker_page, edit_checkin, delete_checkin, mark_dose_taken,
    add_question, toggle_question, delete_question,
)

urlpatterns = [
    path("", tracker_page, name="tracker"),
    path("checkin/<int:checkin_id>/edit/", edit_checkin, name="edit-checkin"),
    path("checkin/<int:checkin_id>/delete/", delete_checkin, name="delete-checkin"),
    path("medication/<int:medication_id>/mark-taken/", mark_dose_taken, name="mark-dose-taken"),
    path("question/add/", add_question, name="add-question"),
    path("question/<int:question_id>/toggle/", toggle_question, name="toggle-question"),
    path("question/<int:question_id>/delete/", delete_question, name="delete-question"),
]