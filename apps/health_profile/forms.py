from django import forms
from .models import HealthProfile


class HealthProfileForm(forms.ModelForm):
    allergies = forms.MultipleChoiceField(
        choices=HealthProfile.ALLERGY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Do you have any food or medicine allergies?",
        help_text="Tick anything that applies -- this helps us avoid suggesting foods that aren't safe for you.",
    )
    previous_complications = forms.MultipleChoiceField(
        choices=HealthProfile.COMPLICATION_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Have any of these happened in a past pregnancy?",
        help_text="Leave blank if this is your first pregnancy, or none of these apply.",
    )

    class Meta:
        model = HealthProfile
        fields = [
            "last_menstrual_period", "expected_delivery_date", "edd_is_manual_override",
            "previous_pregnancies_count", "live_births_count",
            "previous_complications", "previous_complications_other",
            "height_cm", "blood_group",
            "pre_existing_conditions", "allergies", "allergy_other",
            "has_gestational_diabetes", "has_hypertension", "dietary_preference",
            "smokes", "drinks_alcohol",
        ]
        labels = {
            "last_menstrual_period": "First day of your last period",
            "expected_delivery_date": "Your due date",
            "edd_is_manual_override": "My doctor gave me a different due date",
            "previous_pregnancies_count": "How many times have you been pregnant before this one?",
            "live_births_count": "How many of those pregnancies ended in a live birth?",
            "previous_complications_other": "Anything else about a past pregnancy worth mentioning?",
            "height_cm": "Your height",
            "blood_group": "Blood group",
            "pre_existing_conditions": "Do you have any health conditions from before this pregnancy?",
            "allergy_other": "Any other allergy not listed above",
            "has_gestational_diabetes": "Have you been told you have diabetes during this pregnancy?",
            "has_hypertension": "Have you been told you have high blood pressure?",
            "dietary_preference": "Do you follow any special diet?",
            "smokes": "Do you smoke?",
            "drinks_alcohol": "Do you drink alcohol?",
        }
        help_texts = {
            "last_menstrual_period": "This helps us work out your due date and how many weeks along you are.",
            "expected_delivery_date": "We calculate this automatically from your last period. Tick the box below only if your doctor gave you a different date.",
            "previous_pregnancies_count": "Not counting your current pregnancy. Enter 0 if this is your first.",
            "live_births_count": "A baby born alive, at any stage. Enter 0 if this is your first pregnancy.",
            "height_cm": "In centimeters -- used along with your weight to give you more personal suggestions.",
            "pre_existing_conditions": "For example: thyroid problems, asthma, or anything else your doctor should know about.",
        }
        widgets = {
            "last_menstrual_period": forms.DateInput(attrs={"type": "date", "class": "hp-input"}),
            "expected_delivery_date": forms.DateInput(attrs={"type": "date", "id": "id_expected_delivery_date", "class": "hp-input"}),
            "edd_is_manual_override": forms.CheckboxInput(attrs={"id": "id_edd_override", "class": "hp-checkbox"}),
            "previous_pregnancies_count": forms.NumberInput(attrs={"min": 0, "class": "hp-input"}),
            "live_births_count": forms.NumberInput(attrs={"min": 0, "class": "hp-input"}),
            "previous_complications_other": forms.TextInput(attrs={"class": "hp-input", "placeholder": "Optional"}),
            "height_cm": forms.NumberInput(attrs={"step": "0.1", "placeholder": "e.g. 155", "class": "hp-input"}),
            "blood_group": forms.Select(attrs={"class": "hp-input"}),
            "pre_existing_conditions": forms.Textarea(attrs={"rows": 3, "class": "hp-input"}),
            "allergy_other": forms.TextInput(attrs={"class": "hp-input", "placeholder": "e.g. penicillin"}),
            "dietary_preference": forms.Select(attrs={"class": "hp-input"}),
            "has_gestational_diabetes": forms.CheckboxInput(attrs={"class": "hp-checkbox"}),
            "has_hypertension": forms.CheckboxInput(attrs={"class": "hp-checkbox"}),
            "smokes": forms.CheckboxInput(attrs={"class": "hp-checkbox"}),
            "drinks_alcohol": forms.CheckboxInput(attrs={"class": "hp-checkbox"}),
        }