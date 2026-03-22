from django.urls import path
from . import views

urlpatterns = [
    # DEPRECATED path('', views.finance_list, name='finance_list'),
    path('donations/', views.donations_list, name='donations_list'),
    path('expenses/', views.expenses_list, name='expenses_list'),
    path('consolidated/', views.consolidated_dashboard, name='consolidated_dashboard'),
]
