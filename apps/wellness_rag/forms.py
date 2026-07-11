from django import forms


class WellnessQueryForm(forms.Form):
    query = forms.CharField(
        label="",
        max_length=1000,
        widget=forms.TextInput(attrs={
            "class": "flex-1 border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-rose-200",
            "placeholder": "e.g. What should I eat this week?",
        }),
    )