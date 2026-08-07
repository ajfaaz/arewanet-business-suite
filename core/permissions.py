from rest_framework.permissions import BasePermission
from invoices.views import _get_user_organization


def can_create_invoice(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN', 'ACCOUNTANT'])


def can_delete_invoice(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN'])


def can_view_reports(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN', 'ACCOUNTANT', 'MANAGER'])


def can_manage_customers(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN', 'ACCOUNTANT', 'STAFF'])


class IsOrganizationMember(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        org = _get_user_organization(request.user)
        return org is not None or request.user.is_superuser


class IsOrganizationAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return hasattr(request.user, 'profile') and request.user.profile.role in ['OWNER', 'ADMIN']


class CanManageInvoices(BasePermission):
    def has_permission(self, request, view):
        return can_create_invoice(request.user)


class CanManageProducts(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanManagePayments(BasePermission):
    def has_permission(self, request, view):
        return can_view_reports(request.user)


class CanManageCustomers(BasePermission):
    def has_permission(self, request, view):
        return can_manage_customers(request.user)
