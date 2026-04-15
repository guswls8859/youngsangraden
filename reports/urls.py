from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # 캘린더 (투두 진입점)
    path('calendar/', views.TaskCalendarView.as_view(), name='task_calendar'),
    path('calendar/<str:date_str>/tasks/', views.task_day_tasks, name='task_day_tasks'),
    # 투두리스트 (구버전 — 캘린더로 리다이렉트)
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/progress/', views.task_update_progress, name='task_progress'),
    path('tasks/<int:pk>/status/', views.task_update_status, name='task_status'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('tasks/<int:pk>/review/', views.task_review_toggle, name='task_review'),
    # 서브 업무
    path('tasks/<int:pk>/subtasks/create/', views.subtask_create, name='subtask_create'),
    path('subtasks/<int:pk>/edit/', views.subtask_edit, name='subtask_edit'),
    path('subtasks/<int:pk>/toggle/', views.subtask_toggle, name='subtask_toggle'),
    path('subtasks/<int:pk>/delete/', views.subtask_delete, name='subtask_delete'),
    path('tasks/report/', views.TaskManagerReportView.as_view(), name='task_report'),
    path('tasks/report/pdf/', views.task_daily_pdf, name='task_daily_pdf'),
    path('tasks/report/weekly/', views.TaskWeeklyReportView.as_view(), name='task_weekly_report'),
    path('tasks/report/weekly/pdf/', views.task_weekly_pdf, name='task_weekly_pdf'),
    # 용산어린이정원 일일보고
    path('integrated/', views.IntegratedDailyReportView.as_view(), name='integrated_daily'),
    path('integrated/pdf/', views.integrated_daily_pdf, name='integrated_daily_pdf'),
    path('integrated/hwp/', views.integrated_daily_hwp, name='integrated_daily_hwp'),
]
