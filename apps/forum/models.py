from django.conf import settings
from django.db import models


class ForumPost(models.Model):
    class Stage(models.TextChoices):
        FIRST_TRIMESTER = "first_trimester", "First Trimester"
        SECOND_TRIMESTER = "second_trimester", "Second Trimester"
        THIRD_TRIMESTER = "third_trimester", "Third Trimester"
        POSTPARTUM = "postpartum", "Postpartum"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="forum_posts")
    stage = models.CharField(max_length=20, choices=Stage.choices)
    title = models.CharField(max_length=150)
    body = models.TextField()
    is_approved = models.BooleanField(default=True)  # flip to False + add a review queue later if needed
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ForumComment(models.Model):
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]