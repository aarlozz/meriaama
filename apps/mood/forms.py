from django import forms
from .models import MoodEntry

# Emoji shown next to each score in the UI -- kept separate from the model
# choices so the database stores plain text labels, not emoji.
MOOD_EMOJI = {
    MoodEntry.MoodScore.VERY_LOW: "😢",
    MoodEntry.MoodScore.LOW: "😕",
    MoodEntry.MoodScore.NEUTRAL: "😐",
    MoodEntry.MoodScore.GOOD: "🙂",
    MoodEntry.MoodScore.VERY_GOOD: "😄",
}


class MoodEntryForm(forms.ModelForm):
    tags = forms.MultipleChoiceField(
        choices=MoodEntry.TAG_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = MoodEntry
        fields = ["score", "tags", "note"]
        widgets = {
            "score": forms.RadioSelect,
            "note": forms.Textarea(attrs={
                "rows": 3,
                "class": "w-full border rounded px-3 py-2",
                "placeholder": "Anything else on your mind? (optional)",
            }),
        }