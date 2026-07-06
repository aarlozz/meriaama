from rest_framework import serializers
from .models import PsychometricTest


class PsychometricTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PsychometricTest
        fields = ["id", "test_type", "answers", "total_score", "risk_level", "taken_at"]
        read_only_fields = ["id", "total_score", "risk_level", "taken_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
