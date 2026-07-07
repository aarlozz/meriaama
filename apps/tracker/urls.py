from django.urls import path
from .views import tracker_page

urlpatterns = [
    path("", tracker_page, name="weekly-tracker"),
]