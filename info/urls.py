from django.urls import path
from . import views

app_name = 'info'

urlpatterns = [
    path('',              views.InfoReportListView.as_view(),   name='list'),
    path('create/',       views.InfoReportCreateView.as_view(), name='create'),
    path('<int:pk>/',     views.InfoReportDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/',  views.InfoReportUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.InfoReportDeleteView.as_view(), name='delete'),
    path('dashboard/',    views.InfoDashboardView.as_view(),    name='dashboard'),
]
