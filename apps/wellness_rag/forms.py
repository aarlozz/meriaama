from django import forms


class WellnessQueryForm(forms.Form):
    query = forms.CharField(
        label="",
        max_length=1000,
        widget=forms.TextInput(attrs={
            "class": "w-full border rounded px-3 py-2",
            "placeholder": "e.g. What should I eat this week?",
        }),
    )