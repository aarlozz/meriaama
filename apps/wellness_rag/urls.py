from django.urls import path
from .views import wellness_chat_page

urlpatterns = [
    path("", wellness_chat_page, name="wellness-chat"),
]