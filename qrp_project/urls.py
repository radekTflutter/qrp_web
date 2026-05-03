from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

def redirect_recorder(request, object_id=None):
    if object_id:
        if 'change' in request.path:
            return HttpResponseRedirect(f'/admin/qrp_app/rejestrator/{object_id}/change/')
        elif 'delete' in request.path:
            return HttpResponseRedirect(f'/admin/qrp_app/rejestrator/{object_id}/delete/')
    elif 'add' in request.path:
        return HttpResponseRedirect('/admin/qrp_app/rejestrator/add/')
    return HttpResponseRedirect('/admin/qrp_app/rejestrator/')

def redirect_production_line(request, object_id=None):
    if object_id:
        if 'change' in request.path:
            return HttpResponseRedirect(f'/admin/qrp_app/liniaprodukcyjna/{object_id}/change/')
        elif 'delete' in request.path:
            return HttpResponseRedirect(f'/admin/qrp_app/liniaprodukcyjna/{object_id}/delete/')
    elif 'add' in request.path:
        return HttpResponseRedirect('/admin/qrp_app/liniaprodukcyjna/add/')
    return HttpResponseRedirect('/admin/qrp_app/liniaprodukcyjna/')

def redirect_plc_variable(request, object_id=None):
    if object_id:
        if 'change' in request.path:
            return HttpResponseRedirect(f'/admin/qrp_app/zmiennaplc/{object_id}/change/')
        elif 'delete' in request.path:
            return HttpResponseRedirect(f'/admin/qrp_app/zmiennaplc/{object_id}/delete/')
    elif 'add' in request.path:
        return HttpResponseRedirect('/admin/qrp_app/zmiennaplc/add/')
    return HttpResponseRedirect('/admin/qrp_app/zmiennaplc/')

urlpatterns = [
    path('admin/qrp_app/recorder/', redirect_recorder),
    path('admin/qrp_app/recorder/add/', redirect_recorder),
    path('admin/qrp_app/recorder/<path:object_id>/change/', redirect_recorder),
    path('admin/qrp_app/recorder/<path:object_id>/delete/', redirect_recorder),
    path('admin/qrp_app/production-line/', redirect_production_line),
    path('admin/qrp_app/production-line/add/', redirect_production_line),
    path('admin/qrp_app/production-line/<path:object_id>/change/', redirect_production_line),
    path('admin/qrp_app/production-line/<path:object_id>/delete/', redirect_production_line),
    path('admin/qrp_app/plc-variable/', redirect_plc_variable),
    path('admin/qrp_app/plc-variable/add/', redirect_plc_variable),
    path('admin/qrp_app/plc-variable/<path:object_id>/change/', redirect_plc_variable),
    path('admin/qrp_app/plc-variable/<path:object_id>/delete/', redirect_plc_variable),
    path('admin/', admin.site.urls),
    path('', include('qrp_app.urls')),
]

# Dodaj obsługę statycznych plików - MUSI być przed error handlers
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.staticfiles.views import serve
from django.urls import re_path

if settings.DEBUG:
    # W trybie DEBUG używamy standardowej obsługi
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # W trybie produkcyjnym z runserver musimy ręcznie serwować pliki statyczne
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]
    # Dodatkowo staticfiles_urlpatterns dla plików z aplikacji
    urlpatterns += staticfiles_urlpatterns()

# Custom error handlers
handler404 = 'qrp_app.views.custom_404'
handler500 = 'qrp_app.views.custom_500'
