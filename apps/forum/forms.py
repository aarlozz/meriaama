from django import forms
from .models import ForumPost, ForumComment


class ForumPostForm(forms.ModelForm):
    class Meta:
        model = ForumPost
        fields = ["stage", "title", "body", "image"]
        widgets = {
            "stage": forms.Select(attrs={"class": "w-full border rounded px-3 py-2"}),
            "title": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2"}),
            "body": forms.Textarea(attrs={"rows": 5, "class": "w-full border rounded px-3 py-2"}),
            "image": forms.ClearableFileInput(attrs={"accept": "image/*", "class": "w-full text-sm"}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Image must be under 5MB.")
        return image


class ForumCommentForm(forms.ModelForm):
    class Meta:
        model = ForumComment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 2, "class": "w-full border rounded px-3 py-2", "placeholder": "Add a comment..."}),
        }