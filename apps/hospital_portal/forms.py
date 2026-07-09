from django import forms
from .models import PrenatalVisit
from . models import Medication


class PrenatalVisitForm(forms.ModelForm):
    class Meta:
        model = PrenatalVisit
        fields = [
            "visit_date", "gestational_week",
            "maternal_weight_kg", "blood_pressure", "fundal_height_cm",
            "fetal_heart_rate_bpm", "fetal_movement", "urine_protein", "urine_glucose",
            "hemoglobin_g_dl", "fetal_position", "edema",
            "doctor_notes", "next_visit_date",
        ]
        widgets = {
            "visit_date": forms.DateInput(attrs={"type": "date", "class": "w-full border rounded px-3 py-2"}),
            "gestational_week": forms.NumberInput(attrs={"class": "w-full border rounded px-3 py-2", "placeholder": "Auto-filled from her profile -- override if needed"}),
            "maternal_weight_kg": forms.NumberInput(attrs={"class": "w-full border rounded px-3 py-2", "step": "0.1"}),
            "blood_pressure": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2", "placeholder": "e.g. 120/80"}),
            "fundal_height_cm": forms.NumberInput(attrs={"class": "w-full border rounded px-3 py-2", "step": "0.1"}),
            "fetal_heart_rate_bpm": forms.NumberInput(attrs={"class": "w-full border rounded px-3 py-2"}),
            "fetal_movement": forms.Select(attrs={"class": "w-full border rounded px-3 py-2"}),
            "urine_protein": forms.Select(attrs={"class": "w-full border rounded px-3 py-2"}),
            "urine_glucose": forms.Select(attrs={"class": "w-full border rounded px-3 py-2"}),
            "hemoglobin_g_dl": forms.NumberInput(attrs={"class": "w-full border rounded px-3 py-2", "step": "0.1"}),
            "fetal_position": forms.Select(attrs={"class": "w-full border rounded px-3 py-2"}),
            "edema": forms.Select(attrs={"class": "w-full border rounded px-3 py-2"}),
            "doctor_notes": forms.Textarea(attrs={"rows": 4, "class": "w-full border rounded px-3 py-2"}),
            "next_visit_date": forms.DateInput(attrs={"type": "date", "class": "w-full border rounded px-3 py-2"}),
        }


class StaffHealthProfileForm(forms.ModelForm):
    """
    Staff-facing form for the clinical/safety fields on HealthProfile.
    This edits the SAME model instance the mother can also edit herself
    (via her own health_profile form) -- whichever side saves last wins,
    per your call that both can edit and overwrite.
    """
    class Meta:
        fields = [
            "blood_group", "pre_existing_conditions", "allergies", "allergy_other",
            "has_gestational_diabetes", "has_hypertension", "dietary_preference",
        ]

    def __init__(self, *args, **kwargs):
        from apps.health_profile.models import HealthProfile
        self.Meta.model = HealthProfile
        super().__init__(*args, **kwargs)
        self.fields["allergies"] = forms.MultipleChoiceField(
            choices=HealthProfile.ALLERGY_CHOICES,
            widget=forms.CheckboxSelectMultiple,
            required=False,
        )
        for name, field in self.fields.items():
            if name != "allergies" and not isinstance(field.widget, (forms.CheckboxInput,)):
                field.widget.attrs.setdefault("class", "w-full border rounded px-3 py-2")


class MedicationForm(forms.ModelForm):
    class Meta:
        model = Medication
        fields = ["name", "dosage", "frequency_per_day", "duration_days", "start_date", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2", "placeholder": "e.g. Iron + Folic Acid"}),
            "dosage": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2", "placeholder": "e.g. 500mg"}),
            "frequency_per_day": forms.NumberInput(attrs={"class": "w-full border rounded px-3 py-2", "min": 1}),
            "duration_days": forms.NumberInput(attrs={"class": "w-full border rounded px-3 py-2", "min": 1, "placeholder": "e.g. 30"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "w-full border rounded px-3 py-2"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "w-full border rounded px-3 py-2"}),
        }                