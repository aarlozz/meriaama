from django.urls import path
from . import views

urlpatterns = [
    path("", views.select_test_page, name="psychometric-select"),
    path("take/<str:test_type>/", views.take_test_page, name="psychometric-take"),
    path("result/<int:test_id>/", views.test_result_page, name="psychometric-result"),
]