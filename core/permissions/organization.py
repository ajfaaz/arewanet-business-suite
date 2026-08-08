from rest_framework.permissions import BasePermission
from invoices.views import _get_user_organization


class IsOrganizationMember(BasePermission):
    """
    Allows access only to authenticated users
    who belong to an organization.
    """

    message = "You must belong to an organization."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        org = getattr(user, "organization", None)
        if org is None and hasattr(user, "userprofile"):
            org = user.userprofile.organization

        return org is not None


class IsOrganizationAdmin(BasePermission):
    """
    Allows access only to organization administrators or superusers.
    """

    message = "Organization administrator permission required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        org = getattr(user, "organization", None)
        if org is None and hasattr(user, "userprofile"):
            org = user.userprofile.organization

        if org is None:
            return False

        return (
            getattr(user, "is_organization_admin", False)
            or (hasattr(user, "userprofile") and user.userprofile.role in ["OWNER", "ADMIN"])
        )
