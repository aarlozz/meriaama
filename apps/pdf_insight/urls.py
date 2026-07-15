# apps/pdf_insight/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.report_list_page, name="report-list"),
    path("upload/", views.report_upload_page, name="report-upload"),
    path("reports/<int:pk>/", views.report_detail_page, name="report-detail"),
    path("ask/", views.ask_about_report, name="report-ask"),
]