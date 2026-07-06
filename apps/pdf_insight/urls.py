from django.urls import path
from . import views

urlpatterns = [
    path("", views.report_list_page, name="report-list"),
    path("upload/", views.report_upload_page, name="report-upload"),
]