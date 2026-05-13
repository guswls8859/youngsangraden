from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.views.generic import RedirectView
from django.http import HttpResponse


admin.site.site_header = '용산어린이정원 운영관리 시스템'
admin.site.site_title  = '용산어린이정원 관리자'
admin.site.index_title = '관리 메뉴'


def health_check(request):
    return HttpResponse('ok')


urlpatterns = [
    path('health/', health_check),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('reports/', include('reports.urls')),
    path('parking/', include('parking.urls')),
    path('info/', include('info.urls')),
    path('facilities/', include('facilities.urls')),
    path('sportsfield/', include('sportsfield.urls')),
    path('eventhouse/', include('eventhouse.urls')),
    path('menu/', login_required(TemplateView.as_view(template_name='main_menu.html')), name='main_menu'),
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False), name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
