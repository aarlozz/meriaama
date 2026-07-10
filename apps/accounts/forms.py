from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class MotherRegisterForm(UserCreationForm):
    """
    Public registration form. Always creates role='mother'.
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


class StaffRegisterForm(UserCreationForm):
    """
    Public staff sign-up form. Only creates Data Entry Operator accounts --
    doctor/nurse accounts are created by an admin directly (via /admin/ or
    a future admin-side "add staff" form), not through public self-registration.
    Creates an INACTIVE account pending admin approval either way.
    """
    phone_number = forms.CharField(required=False, max_length=20)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "phone_number"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "w-full border rounded px-3 py-2 mb-1"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.DATA_ENTRY
        user.is_active = False  # pending admin approval
        if commit:
            user.save()
        return user


class MotherLoginForm(AuthenticationForm):
    """Rejects login if the account isn't a mother -- reinforces the two-box split."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.role != User.Role.MOTHER:
            raise forms.ValidationError(
                "This login is for mothers. Please use the hospital staff login instead.",
                code="wrong_portal",
            )