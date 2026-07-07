from django.urls import path
from .views import trimester_analysis_page

urlpatterns = [
    path("", trimester_analysis_page, name="trimester-analysis"),
]