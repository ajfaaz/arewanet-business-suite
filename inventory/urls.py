from django.urls import path
from inventory import views

urlpatterns = [
    path('grn/<int:pk>/', views.grn_detail, name='grn_detail'),
    path('gin/<int:pk>/', views.gin_detail, name='gin_detail'),
    path('transfer/<int:pk>/', views.transfer_detail, name='transfer_detail'),
    path('adjustment/<int:pk>/', views.adjustment_detail, name='adjustment_detail'),
]
