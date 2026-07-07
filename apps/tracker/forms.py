from django import forms
from .models import PersonalCheckIn


class PersonalCheckInForm(forms.ModelForm):
    class Meta:
        model = PersonalCheckIn
        fields = ["visit_date", "note"]
        widgets = {
            "visit_date": forms.DateInput(attrs={"type": "date", "class": "w-full border rounded px-3 py-2"}),
            "note": forms.Textarea(attrs={
                "rows": 3, "class": "w-full border rounded px-3 py-2",
                "placeholder": "How are you feeling? Any questions for your next visit?",
            }),
        }