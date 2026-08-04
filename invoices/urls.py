from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [

    path(
        'login/',
        auth_views.LoginView.as_view(),
        name='login'
    ),

    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='login'),
        name='logout'
    ),

    path(
        '',
        views.dashboard,
        name='dashboard'
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

    # Payments CRUD
    path(
        "payments/",
        views.payment_list,
        name="payment_list",
    ),

    path(
        "payments/create/<int:invoice_id>/",
        views.payment_create,
        name="payment_create",
    ),

    path(
        "payments/<int:pk>/",
        views.payment_detail,
        name="payment_detail",
    ),

    path(
        "payments/<int:pk>/edit/",
        views.payment_update,
        name="payment_update",
    ),

    path(
        "payments/<int:pk>/delete/",
        views.payment_delete,
        name="payment_delete",
    ),

    path(
        "receipt/<int:pk>/",
        views.receipt_detail,
        name="receipt_detail",
    ),

    path(
        "receipt/<int:pk>/print/",
        views.receipt_print,
        name="receipt_print",
    ),

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

]