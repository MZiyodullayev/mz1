

from rest_framework.serializers import ModelSerializer
from apps.users.models import User


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        # Explicit allow-list: never expose password hash or permission flags
        # through the API.
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "is_active", "date_joined")


# Backwards-compatible alias (old name had a typo: "Seralizer")
UserSeralizer = UserSerializer
