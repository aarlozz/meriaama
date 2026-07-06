from rest_framework import serializers
from .models import ForumPost, ForumComment


class ForumCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = ForumComment
        fields = ["id", "post", "author_username", "body", "created_at"]
        read_only_fields = ["id", "author_username", "created_at"]


class ForumPostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)
    comments = ForumCommentSerializer(many=True, read_only=True)

    class Meta:
        model = ForumPost
        fields = ["id", "author_username", "stage", "title", "body", "is_approved", "created_at", "comments"]
        read_only_fields = ["id", "author_username", "is_approved", "created_at", "comments"]
