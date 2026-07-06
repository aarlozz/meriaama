from django import forms
from .models import HealthProfile


class HealthProfileForm(forms.ModelForm):
    allergies = forms.MultipleChoiceField(
        choices=HealthProfile.ALLERGY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Allergies (check all that apply)",
    )

    class Meta:
        model = HealthProfile
        fields = [
            "last_menstrual_period", "expected_delivery_date", "blood_group",
            "pre_existing_conditions", "allergies", "allergy_other",
            "has_gestational_diabetes", "has_hypertension", "dietary_preference",
        ]
        widgets = {
            "last_menstrual_period": forms.DateInput(attrs={"type": "date", "class": "w-full border rounded px-3 py-2"}),
            "expected_delivery_date": forms.DateInput(attrs={"type": "date", "class": "w-full border rounded px-3 py-2"}),
            "blood_group": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2", "placeholder": "e.g. O+"}),
            "pre_existing_conditions": forms.Textarea(attrs={"rows": 3, "class": "w-full border rounded px-3 py-2"}),
            "allergy_other": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2", "placeholder": "Any other allergy not listed above"}),
            "dietary_preference": forms.Select(attrs={"class": "w-full border rounded px-3 py-2"}),
        }