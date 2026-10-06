from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import Status


class Permission(models.Model):
    module = models.CharField(max_length=50)
    action = models.CharField(max_length=10)

    class Meta:
        db_table = "permissions"
        unique_together = ("module", "action")
        ordering = ["module", "action"]

    def __str__(self):
        return f"{self.module}:{self.action}"


class Role(models.Model):
    name = models.CharField(max_length=60, unique=True)
    description = models.CharField(max_length=255, blank=True)
    full_access = models.BooleanField(default=False, editable=False)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles", db_table="role_permissions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "roles"
        ordering = ["id"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    full_name = models.CharField(max_length=120, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.PROTECT, related_name="users")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = "users"

    def save(self, *args, **kwargs):
        self.is_active = self.status == Status.ACTIVE
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name or self.username

    @property
    def has_full_access(self):
        return self.is_superuser or bool(self.role_id and self.role.full_access)

    def permission_codes(self):
        if not hasattr(self, "_perm_cache"):
            if self.role_id:
                self._perm_cache = {str(p) for p in self.role.permissions.all()}
            else:
                self._perm_cache = set()
        return self._perm_cache

    def can(self, module, action):
        return self.has_full_access or f"{module}:{action}" in self.permission_codes()
