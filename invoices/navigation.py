MENU_SECTIONS = [
    {
        "title": "Sales & Revenue",
        "items": [
            {
                "label": "Customers",
                "url_name": "customer_list",
                "icon": "bi-people",
                "permission": "customer.view",
                "url_match": "customer",
            },
            {
                "label": "Quotations",
                "url_name": "quotation_list",
                "icon": "bi-file-earmark-code",
                "permission": "quotation.view",
                "url_match": "quotation",
            },
            {
                "label": "Quotation Templates",
                "url_name": "quotation_template_list",
                "icon": "bi-layout-text-window-reverse",
                "permission": "quotation_template.view",
                "url_match": "quotation_template",
            },
            {
                "label": "Invoices",
                "url_name": "invoice_list",
                "icon": "bi-file-earmark-text",
                "permission": "invoice.view",
                "url_match": "invoice",
            },
            {
                "label": "Payment Center",
                "url_name": "payment_dashboard",
                "icon": "bi-cash-stack",
                "permission": "payment.view",
                "url_match": "payment",
            },
            {
                "label": "Credit Notes",
                "url_name": "credit_note_list",
                "icon": "fas fa-file-invoice-dollar text-danger",
                "permission": "invoice.view",
                "url_match": "credit_note",
            },
            {
                "label": "Debit Notes",
                "url_name": "debit_note_list",
                "icon": "fas fa-file-invoice-dollar text-info",
                "permission": "invoice.view",
                "url_match": "debit_note",
            },
            {
                "label": "Aging Report",
                "url_name": "aging_report",
                "icon": "fas fa-clock text-warning",
                "permission": "invoice.view",
                "url_match": "aging",
            },
            {
                "label": "Subscriptions",
                "url_name": "subscription_list",
                "icon": "fas fa-sync text-primary",
                "permission": "invoice.view",
                "url_match": "subscription",
            },
        ],
    },
    {
        "title": "Purchasing",
        "items": [
            {
                "label": "Suppliers",
                "url_name": "supplier_list",
                "icon": "fas fa-truck",
                "permission": "supplier.view",
                "url_match": "supplier",
            },
            {
                "label": "Purchase Orders",
                "url_name": "purchase_order_list",
                "icon": "fas fa-shopping-cart",
                "permission": "purchase_order.view",
                "url_match": "purchase_order",
            },
        ],
    },
    {
        "title": "Inventory & Operations",
        "items": [
            {
                "label": "Products & Services",
                "url_name": "product_list",
                "icon": "fas fa-box",
                "permission": "product.view",
                "url_match": "product",
            },
            {
                "label": "Categories",
                "url_name": "category_list",
                "icon": "fas fa-tags",
                "permission": "product.view",
                "url_match": "category",
            },
            {
                "label": "Goods Received (GRN)",
                "url_name": "grn_list",
                "icon": "fas fa-truck-loading",
                "permission": "grn.view",
                "url_match": "grn",
                "disabled": True,
                "soon": True,
            },
            {
                "label": "Goods Issued (GIN)",
                "url_name": "gin_list",
                "icon": "fas fa-dolly",
                "permission": "gin.view",
                "url_match": "gin",
                "disabled": True,
                "soon": True,
            },
        ],
    },
    {
        "title": "Finance",
        "items": [
            {
                "label": "Payment Dashboard",
                "url_name": "payment_dashboard",
                "icon": "bi-bank",
                "permission": "payment.view",
                "url_match": "payment",
            },
        ],
    },
    {
        "title": "System",
        "items": [
            {
                "label": "Settings & Admin",
                "url_name": "admin_settings_dashboard",
                "icon": "bi-gear-fill",
                "permission": "organization.view",
                "url_match": "settings",
            },
        ],
    },
]


def has_perm(membership, permission_code):
    if not membership:
        return True
    if hasattr(membership, 'role') and membership.role and membership.role.slug == 'administrator':
        return True
    normalized_code = permission_code.replace('_', '.')
    return membership.has_permission(normalized_code) or membership.has_permission(permission_code)


def get_user_menu(membership, current_url_name=None, is_superuser=False):
    sections = []

    for sec in MENU_SECTIONS:
        permitted_items = []
        for item in sec["items"]:
            # Superusers always see items
            if is_superuser or item.get("permission") in ["system.admin", "organization.view"]:
                if is_superuser or has_perm(membership, item.get("permission", "")):
                    permitted_items.append(item)
            elif has_perm(membership, item.get("permission", "")):
                permitted_items.append(item)


        if permitted_items:
            sections.append({
                "title": sec["title"],
                "items": permitted_items,
            })

    return sections
