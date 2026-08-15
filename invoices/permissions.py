PERMISSION_DEFINITIONS = [
    # --- Customers ---
    {"code": "customer.view", "name": "View Customers", "module": "customer", "action": "view", "description": "Can view customer list and details"},
    {"code": "customer.create", "name": "Create Customers", "module": "customer", "action": "create", "description": "Can add new customers"},
    {"code": "customer.edit", "name": "Edit Customers", "module": "customer", "action": "edit", "description": "Can update existing customer records"},
    {"code": "customer.delete", "name": "Delete Customers", "module": "customer", "action": "delete", "description": "Can delete customer records"},

    # --- Suppliers ---
    {"code": "supplier.view", "name": "View Suppliers", "module": "supplier", "action": "view", "description": "Can view supplier list and details"},
    {"code": "supplier.create", "name": "Create Suppliers", "module": "supplier", "action": "create", "description": "Can add new suppliers"},
    {"code": "supplier.edit", "name": "Edit Suppliers", "module": "supplier", "action": "edit", "description": "Can update existing supplier records"},
    {"code": "supplier.delete", "name": "Delete Suppliers", "module": "supplier", "action": "delete", "description": "Can delete supplier records"},

    # --- Products ---
    {"code": "product.view", "name": "View Products", "module": "product", "action": "view", "description": "Can view product catalog and stock levels"},
    {"code": "product.create", "name": "Create Products", "module": "product", "action": "create", "description": "Can add new products"},
    {"code": "product.edit", "name": "Edit Products", "module": "product", "action": "edit", "description": "Can update existing products"},
    {"code": "product.delete", "name": "Delete Products", "module": "product", "action": "delete", "description": "Can delete products"},

    # --- Sales Quotations ---
    {"code": "quotation.view", "name": "View Quotations", "module": "quotation", "action": "view", "description": "Can view sales quotations"},
    {"code": "quotation.create", "name": "Create Quotations", "module": "quotation", "action": "create", "description": "Can create new sales quotations"},
    {"code": "quotation.edit", "name": "Edit Quotations", "module": "quotation", "action": "edit", "description": "Can update sales quotations"},
    {"code": "quotation.delete", "name": "Delete Quotations", "module": "quotation", "action": "delete", "description": "Can delete sales quotations"},
    {"code": "quotation.convert", "name": "Convert Quotations", "module": "quotation", "action": "convert", "description": "Can convert quotations to invoices"},

    # --- Sales Invoices ---
    {"code": "invoice.view", "name": "View Invoices", "module": "invoice", "action": "view", "description": "Can view sales invoices"},
    {"code": "invoice.create", "name": "Create Invoices", "module": "invoice", "action": "create", "description": "Can issue new invoices"},
    {"code": "invoice.edit", "name": "Edit Invoices", "module": "invoice", "action": "edit", "description": "Can update existing invoices"},
    {"code": "invoice.delete", "name": "Delete Invoices", "module": "invoice", "action": "delete", "description": "Can delete invoices"},
    {"code": "invoice.cancel", "name": "Cancel Invoices", "module": "invoice", "action": "cancel", "description": "Can cancel issued invoices"},

    # --- Payments & Receipts ---
    {"code": "payment.view", "name": "View Payments", "module": "payment", "action": "view", "description": "Can view payments"},
    {"code": "payment.create", "name": "Create Payments", "module": "payment", "action": "create", "description": "Can record new payments"},
    {"code": "payment.edit", "name": "Edit Payments", "module": "payment", "action": "edit", "description": "Can update payments"},
    {"code": "payment.delete", "name": "Delete Payments", "module": "payment", "action": "delete", "description": "Can delete/reverse payments"},
    {"code": "receipt.view", "name": "View Receipts", "module": "receipt", "action": "view", "description": "Can view payment receipts"},
    {"code": "receipt.create", "name": "Create Receipts", "module": "receipt", "action": "create", "description": "Can issue receipts"},

    # --- Purchasing ---
    {"code": "purchase_order.view", "name": "View Purchase Orders", "module": "purchase_order", "action": "view", "description": "Can view purchase orders"},
    {"code": "purchase_order.create", "name": "Create Purchase Orders", "module": "purchase_order", "action": "create", "description": "Can create purchase orders"},
    {"code": "purchase_order.edit", "name": "Edit Purchase Orders", "module": "purchase_order", "action": "edit", "description": "Can edit purchase orders"},
    {"code": "purchase_order.delete", "name": "Delete Purchase Orders", "module": "purchase_order", "action": "delete", "description": "Can delete purchase orders"},
    {"code": "purchase_order.approve", "name": "Approve Purchase Orders", "module": "purchase_order", "action": "approve", "description": "Can approve purchase orders"},

    # --- Inventory Documents ---
    {"code": "grn.view", "name": "View Goods Received Notes", "module": "grn", "action": "view", "description": "Can view Goods Received Notes"},
    {"code": "grn.create", "name": "Create Goods Received Notes", "module": "grn", "action": "create", "description": "Can draft Goods Received Notes"},
    {"code": "grn.edit", "name": "Edit Goods Received Notes", "module": "grn", "action": "edit", "description": "Can edit Goods Received Notes"},
    {"code": "grn.approve", "name": "Approve Goods Received Notes", "module": "grn", "action": "approve", "description": "Can approve GRNs and increase stock"},

    {"code": "gin.view", "name": "View Goods Issue Notes", "module": "gin", "action": "view", "description": "Can view Goods Issue Notes"},
    {"code": "gin.create", "name": "Create Goods Issue Notes", "module": "gin", "action": "create", "description": "Can draft Goods Issue Notes"},
    {"code": "gin.edit", "name": "Edit Goods Issue Notes", "module": "gin", "action": "edit", "description": "Can edit Goods Issue Notes"},
    {"code": "gin.approve", "name": "Approve Goods Issue Notes", "module": "gin", "action": "approve", "description": "Can approve GINs and issue stock"},

    {"code": "stock_transfer.view", "name": "View Stock Transfers", "module": "stock_transfer", "action": "view", "description": "Can view stock transfer requests"},
    {"code": "stock_transfer.create", "name": "Create Stock Transfers", "module": "stock_transfer", "action": "create", "description": "Can initiate stock transfers"},
    {"code": "stock_transfer.edit", "name": "Edit Stock Transfers", "module": "stock_transfer", "action": "edit", "description": "Can edit stock transfers"},
    {"code": "stock_transfer.approve", "name": "Approve Stock Transfers", "module": "stock_transfer", "action": "approve", "description": "Can approve and dispatch stock transfers"},

    {"code": "stock_adjustment.view", "name": "View Stock Adjustments", "module": "stock_adjustment", "action": "view", "description": "Can view stock adjustments"},
    {"code": "stock_adjustment.create", "name": "Create Stock Adjustments", "module": "stock_adjustment", "action": "create", "description": "Can draft stock adjustments"},
    {"code": "stock_adjustment.edit", "name": "Edit Stock Adjustments", "module": "stock_adjustment", "action": "edit", "description": "Can edit stock adjustments"},
    {"code": "stock_adjustment.approve", "name": "Approve Stock Adjustments", "module": "stock_adjustment", "action": "approve", "description": "Can approve stock adjustments"},

    # --- Reports ---
    {"code": "report.sales", "name": "View Sales Reports", "module": "report", "action": "sales", "description": "Access sales analytics"},
    {"code": "report.purchase", "name": "View Purchase Reports", "module": "report", "action": "purchase", "description": "Access procurement analytics"},
    {"code": "report.inventory", "name": "View Inventory Reports", "module": "report", "action": "inventory", "description": "Access stock analytics"},
    {"code": "report.finance", "name": "View Financial Reports", "module": "report", "action": "finance", "description": "Access financial statements and reports"},

    # --- Quotation Templates ---
    {"code": "quotation_template.view", "name": "View Quotation Templates", "module": "quotation_template", "action": "view", "description": "Can view quotation template gallery and details"},
    {"code": "quotation_template.create", "name": "Create Quotation Templates", "module": "quotation_template", "action": "create", "description": "Can create new quotation templates"},
    {"code": "quotation_template.edit", "name": "Edit Quotation Templates", "module": "quotation_template", "action": "edit", "description": "Can edit existing quotation templates"},
    {"code": "quotation_template.delete", "name": "Delete Quotation Templates", "module": "quotation_template", "action": "delete", "description": "Can delete quotation templates"},
    {"code": "quotation_template.set_default", "name": "Set Default Quotation Template", "module": "quotation_template", "action": "set_default", "description": "Can set default template for organization"},

    # --- Administration ---
    {"code": "organization.view", "name": "View Organization Settings", "module": "organization", "action": "view", "description": "View organization profile"},
    {"code": "organization.edit", "name": "Edit Organization Settings", "module": "organization", "action": "edit", "description": "Update organization profile and settings"},
    {"code": "user.view", "name": "View Organization Users", "module": "user", "action": "view", "description": "View user memberships"},
    {"code": "user.create", "name": "Invite/Create Users", "module": "user", "action": "create", "description": "Add new users to organization"},
    {"code": "user.edit", "name": "Edit User Memberships", "module": "user", "action": "edit", "description": "Update member roles"},
    {"code": "user.disable", "name": "Disable User Memberships", "module": "user", "action": "disable", "description": "Deactivate user membership"},
    {"code": "role.view", "name": "View Roles", "module": "role", "action": "view", "description": "View organization roles"},
    {"code": "role.create", "name": "Create Custom Roles", "module": "role", "action": "create", "description": "Create new custom roles"},
    {"code": "role.edit", "name": "Edit Custom Roles", "module": "role", "action": "edit", "description": "Update custom role permissions"},
    {"code": "role.delete", "name": "Delete Custom Roles", "module": "role", "action": "delete", "description": "Delete non-system custom roles"},
]

ROLE_SYSTEM_PERMISSIONS = {
    "accountant": [
        "customer.view", "supplier.view", "quotation.view", "quotation_template.view",
        "invoice.view", "invoice.create", "invoice.edit",
        "payment.view", "payment.create", "payment.edit",
        "receipt.view", "receipt.create",
        "report.sales", "report.purchase", "report.finance"
    ],
    "sales-officer": [
        "customer.view", "customer.create", "customer.edit",
        "quotation.view", "quotation.create", "quotation.edit", "quotation_template.view",
        "invoice.view", "invoice.create", "invoice.edit",
        "payment.view", "receipt.view", "receipt.create"
    ],
    "inventory-officer": [
        "product.view", "product.create", "product.edit",
        "supplier.view", "purchase_order.view",
        "grn.view", "grn.create", "grn.edit",
        "gin.view", "gin.create", "gin.edit",
        "stock_transfer.view", "stock_transfer.create", "stock_transfer.edit",
        "stock_adjustment.view", "stock_adjustment.create",
        "report.inventory"
    ],
    "purchase-officer": [
        "supplier.view", "supplier.create", "supplier.edit",
        "product.view",
        "purchase_order.view", "purchase_order.create", "purchase_order.edit",
        "grn.view", "grn.create",
        "report.purchase"
    ],
}


from functools import wraps
from django.core.exceptions import PermissionDenied


def require_permission(permission_code):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            membership = getattr(request, 'membership', None)
            if not membership and hasattr(request.user, 'organization_memberships'):
                active_org_id = request.session.get('active_organization_id')
                if active_org_id:
                    membership = request.user.organization_memberships.filter(organization_id=active_org_id, is_active=True).first()
                if not membership:
                    membership = request.user.organization_memberships.filter(is_active=True).first()

            if not membership or not membership.is_active:
                raise PermissionDenied("You do not have an active organization membership.")

            if membership.role and membership.role.slug == 'administrator':
                return view_func(request, *args, **kwargs)

            normalized_code = permission_code.replace('_', '.')
            if membership.has_permission(normalized_code) or membership.has_permission(permission_code):
                return view_func(request, *args, **kwargs)

            raise PermissionDenied(f"You do not have the required permission ({permission_code}) to access this page.")
        return _wrapped_view
    return decorator

