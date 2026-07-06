from django.urls import path
from .views import ClinicalRecordListCreateView

urlpatterns = [
    path("records/", ClinicalRecordListCreateView.as_view(), name="clinical-records"),
]
