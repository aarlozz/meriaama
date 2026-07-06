from django.urls import path
from .views import insights_page

urlpatterns = [
    path("", insights_page, name="insights"),
]