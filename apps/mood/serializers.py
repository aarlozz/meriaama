from rest_framework import serializers
from .models import MoodEntry


class MoodEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodEntry
        fields = ["id", "score", "note", "logged_at"]
        read_only_fields = ["id", "logged_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
