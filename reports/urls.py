from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # 투두리스트
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/progress/', views.task_update_progress, name='task_progress'),
    path('tasks/<int:pk>/status/', views.task_update_status, name='task_status'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('tasks/report/', views.TaskManagerReportView.as_view(), name='task_report'),
    path('tasks/report/pdf/', views.task_daily_pdf, name='task_daily_pdf'),
    path('tasks/report/weekly/', views.TaskWeeklyReportView.as_view(), name='task_weekly_report'),
    path('tasks/report/weekly/pdf/', views.task_weekly_pdf, name='task_weekly_pdf'),
    # 용산어린이정원 일일보고
    path('integrated/', views.IntegratedDailyReportView.as_view(), name='integrated_daily'),
    path('integrated/pdf/', views.integrated_daily_pdf, name='integrated_daily_pdf'),
    path('integrated/hwp/', views.integrated_daily_hwp, name='integrated_daily_hwp'),
]
