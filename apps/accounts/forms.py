from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class MotherRegisterForm(UserCreationForm):
    """
    Public registration form. Always creates role='mother' -- hospital staff
    accounts are created separately by an admin via /admin/, never here.
    """
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(required=False, max_length=20)
    preferred_language = forms.ChoiceField(choices=User._meta.get_field("preferred_language").choices)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "email", "phone_number", "preferred_language"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full rounded-2xl border border-gray-200 bg-gray-50 pl-14 pr-5 py-4 text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-4 focus:ring-rose-100 focus:border-rose-400 transition duration-300"
            })
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.MOTHER
        if commit:
            user.save()
        return user