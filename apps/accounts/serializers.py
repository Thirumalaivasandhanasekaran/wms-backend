from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .constants import MODULES
from .models import Permission, Role, User


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "module", "action"]


class RoleSerializer(serializers.ModelSerializer):
    permission_ids = serializers.PrimaryKeyRelatedField(source="permissions", many=True, read_only=True)
    user_count = serializers.IntegerField(source="users.count", read_only=True)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "full_access", "permission_ids", "user_count", "created_at", "updated_at"]
        read_only_fields = ["full_access", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=8, style={"input_type": "password"})
    role_name = serializers.StringRelatedField(source="role", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "mobile", "email", "role", "role_name", "status", "password", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Password is required for new users."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class MeSerializer(serializers.ModelSerializer):
    role_name = serializers.StringRelatedField(source="role", read_only=True)
    full_access = serializers.BooleanField(source="has_full_access", read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "mobile", "email", "role_name", "full_access", "permissions"]
        read_only_fields = ["username"]

    def get_permissions(self, obj):
        if obj.has_full_access:
            return [f"{m}:{a}" for m, _ in MODULES for a in ("VIEW", "CREATE", "UPDATE", "DELETE", "EXPORT")]
        return sorted(obj.permission_codes())


class LoginSerializer(TokenObtainPairSerializer):
    """Standard SimpleJWT login response plus the user profile and permission list."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = MeSerializer(self.user).data
        return data
