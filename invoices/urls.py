from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from sales.payments import views as sales_payment_views
from sales import views as sales_views

urlpatterns = [

    path(
        'login/',
        auth_views.LoginView.as_view(),
        name='login'
    ),

    path(
        'logout/',
        views.user_logout,
        name='logout'
    ),

    path(
        'organization/switch/',
        views.switch_organization,
        name='switch_organization'
    ),

    path(
        '',
        views.dashboard,
        name='dashboard'
    ),

    path(
        'dashboard/',
        views.dashboard,
        name='dashboard_explicit'
    ),

    path(
        'search/',
        views.global_search,
        name='global_search'
    ),

    path(
        'invoices/',
        views.invoice_list,
        name='invoice_list'
    ),

    path(
        'invoices/create/',
        views.invoice_create,
        name='invoice_create'
    ),

    path(
        'invoice/<int:pk>/',
        views.invoice_detail,
        name='invoice_detail'
    ),

    path(
        'invoice/<int:pk>/print/',
        views.invoice_print,
        name='invoice_print'
    ),

    path(
        'invoice/<int:pk>/edit/',
        views.invoice_update,
        name='invoice_update'
    ),

    path(
        'invoice/<int:pk>/pdf/',
        views.invoice_pdf,
        name='invoice_pdf'
    ),

    path(
        'invoice/<int:pk>/send/',
        views.invoice_send,
        name='invoice_send'
    ),

    path(
        'invoice/<int:pk>/duplicate/',
        views.invoice_duplicate,
        name='invoice_duplicate'
    ),

    path(
        'invoice/<int:pk>/mark-paid/',
        views.invoice_mark_paid,
        name='invoice_mark_paid'
    ),

    path(
        'invoice/<int:pk>/delete/',
        views.invoice_delete,
        name='invoice_delete'
    ),

    # Payments & Enterprise Payment Center
    path("payments/", sales_payment_views.payment_dashboard, name="payment_dashboard"),
    path("payments/list/", sales_payment_views.payment_list, name="payment_list"),
    path("payments/receive/", sales_payment_views.receive_payment, name="receive_payment"),
    path("payments/create/<int:invoice_id>/", views.payment_create, name="payment_create"),
    path("payments/receive/invoice/<int:invoice_id>/", sales_payment_views.receive_payment, name="receive_invoice_payment"),
    path("payments/multi-invoice/", sales_payment_views.multi_invoice_payment, name="multi_invoice_payment"),
    path("payments/<str:pk>/", sales_payment_views.payment_detail, name="payment_detail"),
    path("payments/<str:pk>/receipt/", sales_payment_views.receipt_view, name="receipt_view"),
    path("payments/<str:pk>/reverse/", sales_payment_views.payment_reverse, name="payment_reverse"),
    path("payments/<str:pk>/refund/", sales_payment_views.payment_refund, name="payment_refund"),
    path("payments/<str:pk>/edit/", views.payment_update, name="payment_update"),
    path("payments/<str:pk>/delete/", views.payment_delete, name="payment_delete"),
    path("payments/<int:pk>/", views.payment_detail, name="legacy_payment_detail"),
    path("receipt/<int:pk>/", views.receipt_detail, name="receipt_detail"),
    path("receipt/<int:pk>/pdf/", views.receipt_pdf, name="receipt_pdf"),
    path("receipt/<str:pk>/print/", views.receipt_print, name="receipt_print"),

    path(
        'quotation/<int:pk>/convert/',
        views.quotation_convert,
        name='quotation_convert'
    ),

    # Categories
    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_update, name="category_update"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),

    # Products
    path("products/", views.product_list, name="product_list"),
    path("products/create/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/edit/", views.product_update, name="product_update"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("products/<int:pk>/info/", views.product_info, name="product_info"),

    path(
        'customers/',
        views.customer_list,
        name='customer_list'
    ),

    path(
        'customers/create/',
        views.customer_create,
        name='customer_create'
    ),

    path(
        'customers/<int:pk>/edit/',
        views.customer_update,
        name='customer_update'
    ),

    path(
        'customers/<int:pk>/delete/',
        views.customer_delete,
        name='customer_delete'
    ),

    path(
        'customers/<int:pk>/history/',
        views.customer_history,
        name='customer_history'
    ),

    path(
        'customers/<int:pk>/',
        views.customer_detail,
        name='customer_detail'
    ),

    # Quotations CRUD
    path('quotations/', views.quotation_list, name='quotation_list'),
    path('quotation/create/', views.quotation_create, name='quotation_create'),
    path('quotation/<int:pk>/', views.quotation_detail, name='quotation_detail'),
    path('quotation/<int:pk>/print/', views.quotation_print, name='quotation_print'),
    path('quotation/<int:pk>/pdf/', views.quotation_pdf, name='quotation_pdf'),
    path('quotation/<int:pk>/send/', views.quotation_send, name='quotation_send'),
    path('quotation/<int:pk>/convert/', views.quotation_convert, name='quotation_convert'),
    path('quotation/<int:pk>/convert-to-invoice/', views.quotation_convert, name='quotation_convert_to_invoice'),
    path('quotation/<int:pk>/delete/', views.quotation_delete, name='quotation_delete'),

    # Quotation Templates CRUD
    path('quotation-templates/', views.quotation_template_list, name='quotation_template_list'),
    path('quotation-templates/create/', views.quotation_template_create, name='quotation_template_create'),
    path('quotation-templates/<int:pk>/edit/', views.quotation_template_edit, name='quotation_template_edit'),
    path('quotation-templates/<int:pk>/set-default/', views.quotation_template_set_default, name='quotation_template_set_default'),
    path('quotation-templates/<int:pk>/toggle-active/', views.quotation_template_toggle_active, name='quotation_template_toggle_active'),
    path('quotation-templates/<int:pk>/delete/', views.quotation_template_delete, name='quotation_template_delete'),


    # Credit Notes
    path('credit-notes/', sales_views.credit_note_list, name='credit_note_list'),
    path('credit-notes/create/', sales_views.credit_note_create, name='credit_note_create'),
    path('credit-notes/create/<int:invoice_id>/', sales_views.credit_note_create, name='credit_note_create_invoice'),
    path('credit-notes/<str:pk>/', sales_views.credit_note_detail, name='credit_note_detail'),
    path('credit-notes/<str:pk>/pdf/', sales_views.credit_note_pdf, name='credit_note_pdf'),
    path('credit-notes/<str:pk>/cancel/', sales_views.credit_note_cancel, name='credit_note_cancel'),

    # Debit Notes
    path('debit-notes/', sales_views.debit_note_list, name='debit_note_list'),
    path('debit-notes/create/', sales_views.debit_note_create, name='debit_note_create'),
    path('debit-notes/create/<int:invoice_id>/', sales_views.debit_note_create, name='debit_note_create_invoice'),
    path('debit-notes/<str:pk>/', sales_views.debit_note_detail, name='debit_note_detail'),
    path('debit-notes/<str:pk>/pdf/', sales_views.debit_note_pdf, name='debit_note_pdf'),
    path('debit-notes/<str:pk>/cancel/', sales_views.debit_note_cancel, name='debit_note_cancel'),

    # Statements & Aging Reports
    path('customers/<int:customer_id>/statement/', sales_views.customer_statement_view, name='customer_statement'),
    path('customers/<int:customer_id>/statement/pdf/', sales_views.customer_statement_pdf, name='customer_statement_pdf'),
    path('reports/aging/', sales_views.aging_report_view, name='aging_report'),

    # Subscriptions & Recurring Billing
    path('subscriptions/', include('sales.subscriptions.urls')),
]