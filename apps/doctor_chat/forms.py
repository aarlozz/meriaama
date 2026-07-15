from django import forms
from django.contrib.auth import get_user_model
from .models import ChatMessage

User = get_user_model()


class AssignDoctorForm(forms.Form):
    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(role="doctor", is_active=True),
        label="Assign a doctor",
        widget=forms.Select(attrs={"class": "hp-input"}),
    )


class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["text"]
        widgets = {
            "text": forms.TextInput(attrs={
                "class": "flex-1 border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-rose-200",
                "placeholder": "Type a message...", "autocomplete": "off",
            }),
        }