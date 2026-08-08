from rest_framework.permissions import BasePermission


def can_create_invoice(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN', 'ACCOUNTANT'])


def can_delete_invoice(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN'])


def can_view_reports(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN', 'ACCOUNTANT', 'MANAGER'])


def can_manage_customers(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN', 'ACCOUNTANT', 'STAFF'])


class CanManageCustomers(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.has_perm("invoices.manage_customer"):
            return True
        return can_manage_customers(request.user)


class CanManageProducts(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.has_perm("invoices.manage_product"):
            return True
        return True


class CanManageInvoices(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.has_perm("invoices.manage_invoice"):
            return True
        return can_create_invoice(request.user)


class CanManagePayments(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.has_perm("invoices.manage_payment"):
            return True
        return can_view_reports(request.user)
