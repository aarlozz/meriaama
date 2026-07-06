from rest_framework import serializers
from .models import MedicalReport


class MedicalReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalReport
        fields = ["id", "file", "status", "summary_text", "flagged_values", "uploaded_at"]
        read_only_fields = ["id", "status", "summary_text", "flagged_values", "uploaded_at"]
