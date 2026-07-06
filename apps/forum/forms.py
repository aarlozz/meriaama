from django import forms
from .models import ForumPost, ForumComment


class ForumPostForm(forms.ModelForm):
    class Meta:
        model = ForumPost
        fields = ["stage", "title", "body"]
        widgets = {
            "stage": forms.Select(attrs={"class": "w-full border rounded px-3 py-2"}),
            "title": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2"}),
            "body": forms.Textarea(attrs={"rows": 5, "class": "w-full border rounded px-3 py-2"}),
        }


class ForumCommentForm(forms.ModelForm):
    class Meta:
        model = ForumComment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 2, "class": "w-full border rounded px-3 py-2", "placeholder": "Add a comment..."}),
        }