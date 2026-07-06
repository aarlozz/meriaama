from rest_framework import serializers
from .models import HealthProfile


class HealthProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthProfile
        fields = [
            "id", "last_menstrual_period", "expected_delivery_date",
            "current_gestational_week", "latest_mood_score", "latest_stress_level",
            "blood_group", "pre_existing_conditions", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "current_gestational_week", "latest_mood_score",
                             "latest_stress_level", "created_at", "updated_at"]
