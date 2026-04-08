from django.urls import path
from . import views

app_name = 'parking'

urlpatterns = [
    path('', views.VehicleListView.as_view(), name='list'),
    path('create/', views.VehicleCreateView.as_view(), name='create'),
    path('<int:pk>/', views.VehicleDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.VehicleUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.vehicle_delete, name='delete'),
    path('<int:pk>/action/<str:action>/', views.parking_action, name='action'),
]
