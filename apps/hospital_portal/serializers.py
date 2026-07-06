from rest_framework import serializers
from .models import ClinicalRecord


class ClinicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalRecord
        fields = [
            "id", "mother", "gestational_week", "maternal_weight_kg",
            "blood_pressure", "ultrasound_notes", "appointment_notes", "recorded_at",
        ]
        read_only_fields = ["id", "recorded_at"]
