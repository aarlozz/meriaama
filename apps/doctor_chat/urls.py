from django.urls import path
from . import views

urlpatterns = [
    path("assign/<int:mother_id>/", views.assign_doctor, name="assign-doctor"),
    path("", views.doctor_dashboard, name="doctor-dashboard"),
    path("my-doctor/", views.mother_chat_entry, name="mother-chat-entry"),
    path("thread/<int:assignment_id>/", views.chat_thread, name="chat-thread"),
    path("thread/<int:assignment_id>/poll/", views.chat_poll, name="chat-poll"),
]