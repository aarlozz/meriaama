from django.urls import path
from .views import daily_plan_page

urlpatterns = [
    path("", daily_plan_page, name="daily-plan"),
]