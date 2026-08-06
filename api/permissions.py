from rest_framework import permissions


class IsOrganizationMember(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsSalesStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'userprofile') and request.user.userprofile:
            return request.user.userprofile.role in ["OWNER", "ADMIN", "ACCOUNTANT", "SALES"]
        return True


class IsFinanceStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'userprofile') and request.user.userprofile:
            return request.user.userprofile.role in ["OWNER", "ADMIN", "ACCOUNTANT"]
        return True


class IsAdminOrOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'userprofile') and request.user.userprofile:
            return request.user.userprofile.role in ["OWNER", "ADMIN"]
        return True
