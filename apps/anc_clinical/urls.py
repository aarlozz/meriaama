"""
Include this in your project's root urls.py, e.g.:

    path("anc/", include("anc_clinical.urls")),

ASSUMPTION: your existing visit-edit URL name is `hospital-record-visit-edit`
(used as the redirect target after saving labs/ultrasound, and linked from
record_visit.html). If your actual name differs, either rename it to match
or do a find-replace for `hospital-record-visit-edit` across
anc_clinical/views.py and hospital_portal/templates/hospital_portal/record_visit.html.
"""
from django.urls import path

from . import views

urlpatterns = [
    path("visit/<int:visit_id>/labs/", views.record_labs, name="anc-record-labs"),
    path("visit/<int:visit_id>/ultrasound/", views.record_ultrasound, name="anc-record-ultrasound"),
]
