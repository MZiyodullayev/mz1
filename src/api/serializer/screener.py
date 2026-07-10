from rest_framework import serializers
from apps.screener.models import AnalysisResult, Screenshot, WhitelistUser

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per file


def validate_file_size(f):
    if f.size > MAX_UPLOAD_SIZE_BYTES:
        raise serializers.ValidationError(
            f"File too large ({f.size / (1024 * 1024):.1f} MB). "
            f"Max size is {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB."
        )


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
    """Принимает один или несколько файлов одним запросом.

    ImageField already rejects anything that isn't a real, decodable image
    (it opens each file with Pillow to verify) — so a renamed .exe or
    other non-image payload is already rejected before this point.
    validate_file_size adds a size cap on top of that.
    """
    images = serializers.ListField(
        child=serializers.ImageField(validators=[validate_file_size]),
        allow_empty=False,
        max_length=10,
    )