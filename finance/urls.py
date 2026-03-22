from django.urls import path
from . import views

urlpatterns = [
    path('', views.finance_list, name='finance_list'),
]
