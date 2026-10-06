from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.viewsets import BaseViewSet

from .constants import MODULES
from .models import Permission, Role, User
from .permissions import ModulePermission
from .serializers import LoginSerializer, MeSerializer, PermissionSerializer, RoleSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class MeView(APIView):
    """The current user's profile (used by the Profile settings page and by the front-end after login)."""

    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    def post(self, request):
        old, new = request.data.get("old_password", ""), request.data.get("new_password", "")
        if not request.user.check_password(old):
            return Response({"old_password": "Current password is incorrect."}, status=400)
        try:
            validate_password(new, request.user)
        except DjangoValidationError as exc:
            return Response({"new_password": list(exc.messages)}, status=400)
        request.user.set_password(new)
        request.user.save()
        return Response({"detail": "Password changed successfully."})


class UserViewSet(BaseViewSet):
    queryset = User.objects.select_related("role").all()
    serializer_class = UserSerializer
    permission_module = "users"
    search_fields = ["username", "full_name", "email", "mobile"]
    filter_fields = [("status", "status"), ("role", "role_id")]
    export_name = "users"

    def destroy(self, request, *args, **kwargs):
        if self.get_object().pk == request.user.pk:
            return Response({"detail": "You cannot delete your own account."}, status=400)
        return super().destroy(request, *args, **kwargs)


class RoleViewSet(BaseViewSet):
    queryset = Role.objects.prefetch_related("permissions").all()
    serializer_class = RoleSerializer
    permission_module = "roles"
    search_fields = ["name", "description"]
    ordering = ["id"]
    export_name = "roles"
    permission_actions = {"set_permissions": "UPDATE"}

    def destroy(self, request, *args, **kwargs):
        if self.get_object().full_access:
            return Response({"detail": "The Admin / Owner role cannot be deleted."}, status=400)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["put"], url_path="permissions")
    def set_permissions(self, request, pk=None):
        role = self.get_object()
        if role.full_access:
            return Response({"detail": "The Admin / Owner role always has full access."}, status=400)
        ids = request.data.get("permission_ids", [])
        role.permissions.set(Permission.objects.filter(id__in=ids))
        return Response(RoleSerializer(role).data)


class PermissionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Read-only catalogue of module/action permissions, used by the role permission matrix."""

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "permissions"
    pagination_class = None

    def list(self, request, *args, **kwargs):
        return Response({"modules": [{"code": c, "label": l} for c, l in MODULES], "permissions": PermissionSerializer(self.get_queryset(), many=True).data})
