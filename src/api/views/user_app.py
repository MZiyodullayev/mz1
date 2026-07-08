from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from apps.users.models import User
from api.serializer.user_app import UserSerializer
from api.paginations import MyCustomPaginator


class UserModeViewSet(ModelViewSet):
    """
    Requires a valid JWT (see /api/v1/token/). Staff users see everyone;
    regular users only see and can edit their own account.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MyCustomPaginator

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return User.objects.all()
        return User.objects.filter(pk=user.pk)
