from django import forms
from .models import PersonalCheckIn, DoctorQuestion


class PersonalCheckInForm(forms.ModelForm):
    class Meta:
        model = PersonalCheckIn
        fields = ["note", "image"]
        widgets = {
            "note": forms.Textarea(attrs={
                "rows": 3, "class": "hp-input",
                "placeholder": "Anything you'd like to privately note today...",
            }),
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "size") and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Image must be under 5MB.")
        return image


class DoctorQuestionForm(forms.ModelForm):
    class Meta:
        model = DoctorQuestion
        fields = ["question"]
        widgets = {
            "question": forms.TextInput(attrs={
                "class": "hp-input", "placeholder": "e.g. Is it safe to travel this trimester?",
            }),
        }


