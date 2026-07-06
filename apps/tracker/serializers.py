from rest_framework import serializers
from .models import WeeklyUpdate


class WeeklyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyUpdate
        fields = [
            "id", "gestational_week", "fetal_development_note", "maternal_changes_note",
            "maternal_weight_kg", "blood_pressure", "hospital_notes", "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]
