from django import forms
from .models import PersonalCheckIn


class PersonalCheckInForm(forms.ModelForm):
    class Meta:
        model = PersonalCheckIn
        fields = ["note"]
        widgets = {
            "note": forms.Textarea(attrs={
                "rows": 3, "class": "w-full border rounded px-3 py-2",
                "placeholder": "Anything you'd like to privately note today...",
            }),
        }