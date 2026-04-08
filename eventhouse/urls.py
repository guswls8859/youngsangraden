from django.urls import path
from . import views

app_name = 'eventhouse'

urlpatterns = [
    path('', views.EventhouseMainView.as_view(), name='main'),
    path('record/create/', views.RecordCreateView.as_view(), name='record_create'),
    path('record/<int:pk>/', views.RecordDetailView.as_view(), name='record_detail'),
    path('record/<int:pk>/delete/', views.RecordDeleteView.as_view(), name='record_delete'),
]
