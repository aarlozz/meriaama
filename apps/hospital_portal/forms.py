from django import forms
from .models import PrenatalVisit
from .models import Medication

INPUT_CLASS = "w-full border rounded px-3 py-2"
CHECKBOX_CLASS = "h-4 w-4 text-rose-600 border-gray-300 rounded focus:ring-rose-500"


class PrenatalVisitForm(forms.ModelForm):
    """
    NOTE: bp_systolic, bp_diastolic, is_flagged, and flag_reasons are
    deliberately NOT on this form -- they're auto-computed by
    anc_clinical.signals from `blood_pressure` and the flag engine.
    Staff only ever type into `blood_pressure` ("120/80"), same as before.
    """

    class Meta:
        model = PrenatalVisit
        fields = [
            "visit_date", "gestational_week",
            "maternal_weight_kg", "blood_pressure", "pulse_bpm", "spo2_percent",
            "fundal_height_cm", "fetal_heart_rate_bpm", "fetal_movement",
            "urine_protein", "urine_glucose", "hemoglobin_g_dl", "fetal_position", "edema",
            "lungs_abnormal", "heart_abnormal", "pallor_present", "jaundice_present",
            "doctor_notes", "next_visit_date",
        ]
        widgets = {
            "visit_date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "gestational_week": forms.NumberInput(attrs={"class": INPUT_CLASS, "placeholder": "Auto-filled from her profile -- override if needed"}),
            "maternal_weight_kg": forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.1"}),
            "blood_pressure": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "e.g. 120/80"}),
            "pulse_bpm": forms.NumberInput(attrs={"class": INPUT_CLASS, "placeholder": "bpm"}),
            "spo2_percent": forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.1", "placeholder": "%"}),
            "fundal_height_cm": forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.1"}),
            "fetal_heart_rate_bpm": forms.NumberInput(attrs={"class": INPUT_CLASS}),
            "fetal_movement": forms.Select(attrs={"class": INPUT_CLASS}),
            "urine_protein": forms.Select(attrs={"class": INPUT_CLASS}),
            "urine_glucose": forms.Select(attrs={"class": INPUT_CLASS}),
            "hemoglobin_g_dl": forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.1"}),
            "fetal_position": forms.Select(attrs={"class": INPUT_CLASS}),
            "edema": forms.Select(attrs={"class": INPUT_CLASS}),
            "lungs_abnormal": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
            "heart_abnormal": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
            "pallor_present": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
            "jaundice_present": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
            "doctor_notes": forms.Textarea(attrs={"rows": 4, "class": INPUT_CLASS}),
            "next_visit_date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
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
                field.widget.attrs.setdefault("class", INPUT_CLASS)


class MedicationForm(forms.ModelForm):
    class Meta:
        model = Medication
        fields = ["name", "dosage", "frequency_per_day", "duration_days", "start_date", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "e.g. Iron + Folic Acid"}),
            "dosage": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "e.g. 500mg"}),
            "frequency_per_day": forms.NumberInput(attrs={"class": INPUT_CLASS, "min": 1}),
            "duration_days": forms.NumberInput(attrs={"class": INPUT_CLASS, "min": 1, "placeholder": "e.g. 30"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": INPUT_CLASS}),
        }
