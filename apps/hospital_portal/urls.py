from django.urls import path
from . import views

urlpatterns = [
    path("", views.staff_dashboard, name="hospital-dashboard"),
    path("mother/<int:mother_id>/", views.mother_detail, name="hospital-mother-detail"),
    path("mother/<int:mother_id>/edit-profile/", views.edit_health_profile, name="hospital-edit-profile"),
    path("mother/<int:mother_id>/add-visit/", views.add_visit, name="hospital-add-visit"),
]