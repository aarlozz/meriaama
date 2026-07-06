from django.urls import path
from .views import health_profile_page

urlpatterns = [
    path("", health_profile_page, name="health-profile"),
]
