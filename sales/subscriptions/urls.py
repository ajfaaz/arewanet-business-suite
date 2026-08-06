from django.urls import path
from . import views

urlpatterns = [
    path('', views.subscription_list, name='subscription_list'),
    path('dashboard/', views.subscription_dashboard, name='subscription_dashboard'),
    path('forecast/', views.subscription_forecast, name='subscription_forecast'),
    path('create/', views.subscription_create, name='subscription_create'),
    path('<str:pk>/', views.subscription_detail, name='subscription_detail'),
    path('<str:pk>/pause/', views.subscription_pause, name='subscription_pause'),
    path('<str:pk>/resume/', views.subscription_resume, name='subscription_resume'),
    path('<str:pk>/cancel/', views.subscription_cancel, name='subscription_cancel'),
    path('<str:pk>/generate-invoice/', views.subscription_generate_invoice, name='subscription_generate_invoice'),
    path('templates/list/', views.template_list, name='subscription_template_list'),
    path('templates/create/', views.template_create, name='subscription_template_create'),
]
