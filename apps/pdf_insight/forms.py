from django import forms
from .models import MedicalReport


class MedicalReportUploadForm(forms.ModelForm):
    class Meta:
        model = MedicalReport
        fields = ["file"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"accept": "application/pdf"}),
        }

    def clean_file(self):
        file = self.cleaned_data["file"]
        if not file.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Please upload a PDF file.")
        if file.size > 15 * 1024 * 1024:
            raise forms.ValidationError("File is too large (max 15MB).")
        return file