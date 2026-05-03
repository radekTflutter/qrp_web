from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'qrp_app'

urlpatterns = [
    path('', views.RFIDLoginView.as_view(), name='rfid_login'),
    path('api/login/', views.RFIDLoginAPI.as_view(), name='api_login'),
    path('api/register/', views.RFIDRegisterAPI.as_view(), name='api_register'),
    path('api/order-number/', views.OrderNumberAPI.as_view(), name='api_order_number'),
    path('api/measurement/', views.MeasurementAPI.as_view(), name='api_measurement'),
    path('api/defect/', views.DefectAPI.as_view(), name='api_defect'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('measurement/', views.MeasurementView.as_view(), name='measurement'),
    path('defect/', views.DefectView.as_view(), name='defect'),
    path('archive/', views.ArchiveView.as_view(), name='archive'),
    path('help/', views.HelpView.as_view(), name='help'),
    path('export/csv/', views.ExportCSVView.as_view(), name='export_csv'),
    path('export/pdf/<str:record_type>/<int:record_id>/', views.ExportPDFView.as_view(), name='export_pdf'),
    path('api/sync/status/', views.SyncStatusAPI.as_view(), name='api_sync_status'),
    path('api/sync/pending/', views.SyncPendingRecordsAPI.as_view(), name='api_sync_pending'),
    path('api/sync/now/', views.SyncNowAPI.as_view(), name='api_sync_now'),
    path('api/auto-logout-settings/', views.AutoLogoutSettingsAPI.as_view(), name='api_auto_logout_settings'),
]
