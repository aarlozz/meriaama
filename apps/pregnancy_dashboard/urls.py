from django.urls import path
from . import views

urlpatterns = [
    path("", views.pregnancy_dashboard, name="dashboard"),
]