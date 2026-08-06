from django.urls import path
from sales.payments import views

urlpatterns = [
    path('', views.payment_dashboard, name='payment_dashboard'),
    path('list/', views.payment_list, name='payment_list'),
    path('receive/', views.receive_payment, name='receive_payment'),
    path('receive/invoice/<int:invoice_id>/', views.receive_payment, name='receive_invoice_payment'),
    path('multi-invoice/', views.multi_invoice_payment, name='multi_invoice_payment'),
    path('<uuid:pk>/', views.payment_detail, name='payment_detail'),
    path('<uuid:pk>/receipt/', views.receipt_view, name='receipt_view'),
    path('<uuid:pk>/reverse/', views.payment_reverse, name='payment_reverse'),
    path('<uuid:pk>/refund/', views.payment_refund, name='payment_refund'),
]
