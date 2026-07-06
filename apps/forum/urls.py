from django.urls import path
from . import views

urlpatterns = [
    path("", views.forum_list_page, name="forum-list"),
    path("new/", views.forum_create_page, name="forum-create"),
    path("<int:post_id>/", views.forum_detail_page, name="forum-detail"),
]