from django.urls import path
from . import views

app_name = 'sportsfield'

urlpatterns = [
    path('', views.SportsfieldMainView.as_view(), name='main'),
    path('usage/', views.SportsfieldUsageView.as_view(), name='usage'),
    path('refresh/', views.ScrapeRefreshView.as_view(), name='refresh'),
    path('reservation/<int:rv_no>/', views.ReservationDetailView.as_view(), name='reservation_detail'),
    path('entry/create/', views.EntryCreateView.as_view(), name='entry_create'),
    path('entry/<int:pk>/', views.EntryDetailView.as_view(), name='entry_detail'),
    path('entry/<int:pk>/delete/', views.EntryDeleteView.as_view(), name='entry_delete'),
    path('reservation/<int:rv_no>/usage/', views.ReservationUsageUpdateView.as_view(), name='reservation_usage'),
    path('entry/<int:pk>/usage/', views.EntryUsageUpdateView.as_view(), name='entry_usage'),
]
