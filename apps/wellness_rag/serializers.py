from rest_framework import serializers
from .models import Recommendation


class RecommendationRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000)


class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = ["id", "query", "retrieved_sources", "response_text", "created_at"]
        read_only_fields = fields
