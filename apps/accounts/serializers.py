from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "phone_number", "preferred_language"]
        read_only_fields = ["id", "role"]  # role is set by staff, not self-assigned


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password", "phone_number", "preferred_language"]

    def create(self, validated_data):
        # Public registration is always role="mother".
        # Hospital staff accounts are created by an admin via /admin/, never self-registered.
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            phone_number=validated_data.get("phone_number", ""),
            preferred_language=validated_data.get("preferred_language", "en"),
            role=User.Role.MOTHER,
        )
        return user