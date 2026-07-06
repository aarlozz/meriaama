from django.contrib import admin
from .models import ForumPost, ForumComment


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "stage", "is_approved", "created_at")
    list_filter = ("stage", "is_approved")
    search_fields = ("title", "body", "author__username")


@admin.register(ForumComment)
class ForumCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")