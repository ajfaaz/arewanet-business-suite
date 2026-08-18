from django.urls import path
from purchases import views

urlpatterns = [
    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # Purchase Orders
    path('orders/', views.purchase_order_list, name='purchase_order_list'),
    path('orders/create/', views.purchase_order_create, name='purchase_order_create'),
    path('orders/<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('orders/<int:pk>/submit/', views.purchase_order_submit, name='purchase_order_submit'),
    path('orders/<int:pk>/approve/', views.purchase_order_approve, name='purchase_order_approve'),
    path('orders/<int:pk>/cancel/', views.purchase_order_cancel, name='purchase_order_cancel'),
    path('orders/<int:pk>/close/', views.purchase_order_close, name='purchase_order_close'),
]
