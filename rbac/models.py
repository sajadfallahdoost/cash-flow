from django.db import models
from accounts.models import User
from core.models import Company, Project

class Role(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "roles"
        ordering = ['name']
        verbose_name = "Role"
        verbose_name_plural = "Roles"

class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.code

    class Meta:
        db_table = "permissions"
        ordering = ['code']
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"

class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='permission_roles')

    def __str__(self):
        return f"{self.role.name} -> {self.permission.code}"

    class Meta:
        db_table = "role_permissions"
        unique_together = ('role', 'permission')
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"

class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_roles')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_roles')

    def __str__(self):
        scope = self.project or self.company or "Global"
        return f"{self.user.email} -> {self.role.name} @ {scope}"

    class Meta:
        db_table = "user_roles"
        unique_together = ('user', 'role', 'company', 'project')
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"
