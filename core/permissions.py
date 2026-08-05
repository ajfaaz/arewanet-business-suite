def can_create_invoice(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN', 'ACCOUNTANT'])

def can_delete_invoice(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN'])

def can_view_reports(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN', 'ACCOUNTANT', 'MANAGER'])

def can_manage_customers(user):
    return user.is_authenticated and (user.is_superuser or hasattr(user, 'profile') and user.profile.role in ['OWNER', 'ADMIN', 'ACCOUNTANT', 'STAFF'])
