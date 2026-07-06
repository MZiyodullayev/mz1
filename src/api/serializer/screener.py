from rest_framework import serializers
from apps.screener.models import AnalysisResult, Screenshot, WhitelistUser


class WhitelistUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhitelistUser
        fields = ("id", "telegram_id", "name", "is_active", "created_at")
        read_only_fields = ("id", "created_at")


class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = ("id", "answer", "model_used", "created_at")
        read_only_fields = fields


class ScreenshotSerializer(serializers.ModelSerializer):
    result = AnalysisResultSerializer(read_only=True)

    class Meta:
        model = Screenshot
        fields = ("id", "image", "status", "created_at", "result")
        read_only_fields = ("id", "status", "created_at", "result")


class ScreenshotUploadSerializer(serializers.Serializer):
    """Принимает один или несколько файлов одним запросом."""
    images = serializers.ListField(
        child=serializers.ImageField(),
        allow_empty=False,
        max_length=10,
    )
