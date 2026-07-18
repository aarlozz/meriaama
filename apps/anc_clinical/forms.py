"""
LabPanelForm is a plain forms.Form, not a ModelForm -- LabResult itself is
a generic (test_code, value_numeric/value_text) row, which is a bad direct
match for a data-entry UI (staff shouldn't be typing "HB" into a text box).
Instead this form has one named field per known test; the view maps each
field to a LabResult row keyed by test_code (see views.py).

Blood group/Rh is intentionally NOT here -- it lives on the mother's
HealthProfile (accounts app), edited from her profile page, not per-visit.
"""
from django import forms

TEXT_INPUT_CLASS = "w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-rose-500"
SELECT_CLASS = TEXT_INPUT_CLASS

REACTIVE_CHOICES = [("", "-- not tested --"), ("non_reactive", "Non-reactive"), ("reactive", "Reactive")]
DIPSTICK_CHOICES = [("", "-- not tested --"), ("negative", "Negative"), ("trace", "Trace"),
                     ("plus1", "+1"), ("plus2", "+2"), ("plus3", "+3")]


class LabPanelForm(forms.Form):
    hemoglobin = forms.FloatField(required=False, label="Hemoglobin (g/dL)",
                                   widget=forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "0.1"}))
    urine_protein = forms.ChoiceField(required=False, choices=DIPSTICK_CHOICES,
                                       widget=forms.Select(attrs={"class": SELECT_CLASS}))
    urine_glucose = forms.ChoiceField(required=False, choices=DIPSTICK_CHOICES,
                                       widget=forms.Select(attrs={"class": SELECT_CLASS}))
    hiv = forms.ChoiceField(required=False, label="HIV", choices=REACTIVE_CHOICES,
                             widget=forms.Select(attrs={"class": SELECT_CLASS}))
    hbsag = forms.ChoiceField(required=False, label="HBsAg", choices=REACTIVE_CHOICES,
                               widget=forms.Select(attrs={"class": SELECT_CLASS}))
    vdrl = forms.ChoiceField(required=False, label="VDRL", choices=REACTIVE_CHOICES,
                              widget=forms.Select(attrs={"class": SELECT_CLASS}))
    rft_creatinine = forms.FloatField(required=False, label="Serum Creatinine (mg/dL)",
                                       widget=forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "0.01"}))
    tsh = forms.FloatField(required=False, label="TSH (mIU/L)",
                            widget=forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "0.01"}))
    gct = forms.FloatField(required=False, label="GCT, 1hr 50g (mg/dL)",
                            widget=forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "1"}))
    hba1c = forms.FloatField(required=False, label="HbA1c (%)",
                              widget=forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "0.1"}))

    # Maps form field name -> (test_code, test_name, unit, is_text_result)
    FIELD_MAP = {
        "hemoglobin": ("HB", "Hemoglobin", "g/dL", False),
        "urine_protein": ("URINE_PROTEIN", "Urine Protein", "", True),
        "urine_glucose": ("URINE_GLUCOSE", "Urine Glucose", "", True),
        "hiv": ("HIV", "HIV", "", True),
        "hbsag": ("HBSAG", "HBsAg", "", True),
        "vdrl": ("VDRL", "VDRL", "", True),
        "rft_creatinine": ("RFT_CREATININE", "Serum Creatinine", "mg/dL", False),
        "tsh": ("TSH", "TSH", "mIU/L", False),
        "gct": ("GCT", "Glucose Challenge Test", "mg/dL", False),
        "hba1c": ("HBA1C", "HbA1c", "%", False),
    }


class UltrasoundReportForm(forms.ModelForm):
    class Meta:
        from .models import UltrasoundReport
        model = UltrasoundReport
        fields = [
            "scan_type", "scan_date",
            "intrauterine_confirmed", "number_of_fetuses", "fetal_cardiac_activity",
            "nuchal_translucency_mm", "dual_marker_risk",
            "placenta_position", "liquor_status",
            "head_circumference_mm", "abdominal_circumference_mm", "femur_length_mm",
            "estimated_gestational_age_weeks", "estimated_fetal_weight_g",
            "estimated_fetal_weight_percentile", "fetal_movement_normal",
            "notes",
        ]
        widgets = {
            "scan_type": forms.Select(attrs={"class": SELECT_CLASS}),
            "scan_date": forms.DateInput(attrs={"type": "date", "class": TEXT_INPUT_CLASS}),
            "number_of_fetuses": forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS}),
            "nuchal_translucency_mm": forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "0.1"}),
            "dual_marker_risk": forms.Select(attrs={"class": SELECT_CLASS}, choices=[("", "--"), ("low", "Low risk"), ("high", "High risk")]),
            "placenta_position": forms.TextInput(attrs={"class": TEXT_INPUT_CLASS}),
            "liquor_status": forms.TextInput(attrs={"class": TEXT_INPUT_CLASS, "placeholder": "normal / oligohydramnios / polyhydramnios"}),
            "head_circumference_mm": forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "0.1"}),
            "abdominal_circumference_mm": forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "0.1"}),
            "femur_length_mm": forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "0.1"}),
            "estimated_gestational_age_weeks": forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "0.1"}),
            "estimated_fetal_weight_g": forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "1"}),
            "estimated_fetal_weight_percentile": forms.NumberInput(attrs={"class": TEXT_INPUT_CLASS, "step": "1"}),
            "notes": forms.Textarea(attrs={"class": TEXT_INPUT_CLASS, "rows": 3}),
        }

    def clean_number_of_fetuses(self):
        value = self.cleaned_data.get("number_of_fetuses")
        if value is not None and value > 6:
            raise forms.ValidationError("Number of fetuses seems unusually high -- please double-check this entry.")
        return value