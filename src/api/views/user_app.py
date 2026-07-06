from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from apps.users.models import User
from api.serializer.user_app import UserSeralizer
from api.paginations import MyCustomPaginator


class UserModeViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSeralizer
    permission_classes = [AllowAny]
    pagination_class = MyCustomPaginator
