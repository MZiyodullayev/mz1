from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from apps.users.models import User
from api.serializer.user_app import UserSerializer
from api.paginations import MyCustomPaginator


class UserModeViewSet(ModelViewSet):
    """
    Requires a valid JWT (see /api/v1/token/).
    - Staff: full access to every user (list/create/update/delete).
    - Regular users: can only view/edit their OWN account. They cannot
      create new accounts or see/touch anyone else's (new accounts are
      created via the admin panel or `createsuperuser`/`shell`).
    """
    serializer_class = UserSerializer
    pagination_class = MyCustomPaginator

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return User.objects.all()
        return User.objects.filter(pk=user.pk)