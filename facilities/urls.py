from django.urls import path
from . import views

app_name = 'facilities'

urlpatterns = [
    path('',          views.FacilitiesMenuView.as_view(),        name='menu'),
    # 꿈나래마켓
    path('kumnare/',                  views.KumnareReportListView.as_view(),   name='kumnare'),
    path('kumnare/create/',           views.KumnareReportCreateView.as_view(), name='kumnare_create'),
    path('kumnare/<int:pk>/',         views.KumnareReportDetailView.as_view(), name='kumnare_detail'),
    path('kumnare/<int:pk>/edit/',    views.KumnareReportUpdateView.as_view(),   name='kumnare_edit'),
    path('kumnare/<int:pk>/delete/',  views.KumnareReportDeleteView.as_view(),   name='kumnare_delete'),
    # 카페 어울림
    path('eoulrim/',                  views.EoulrimReportListView.as_view(),   name='eoulrim'),
    path('eoulrim/create/',           views.EoulrimReportCreateView.as_view(), name='eoulrim_create'),
    path('eoulrim/<int:pk>/',         views.EoulrimReportDetailView.as_view(), name='eoulrim_detail'),
    path('eoulrim/<int:pk>/edit/',    views.EoulrimReportUpdateView.as_view(), name='eoulrim_edit'),
    path('eoulrim/<int:pk>/delete/',  views.EoulrimReportDeleteView.as_view(), name='eoulrim_delete'),
    # 잼잼카페
    path('jamjam/',                  views.JamjamReportListView.as_view(),   name='jamjam'),
    path('jamjam/create/',           views.JamjamReportCreateView.as_view(), name='jamjam_create'),
    path('jamjam/<int:pk>/',         views.JamjamReportDetailView.as_view(), name='jamjam_detail'),
    path('jamjam/<int:pk>/edit/',    views.JamjamReportUpdateView.as_view(), name='jamjam_edit'),
    path('jamjam/<int:pk>/delete/',  views.JamjamReportDeleteView.as_view(), name='jamjam_delete'),
]
