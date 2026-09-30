"""
URLs for sync, PWA manifest, service worker and offline endpoints.
"""
from django.urls import path
from .views import (
    PwaManifestView,
    ServiceWorkerView,
    OfflineFallbackView,
    OfflineBootstrapDataView,
    OfflineRecordsSyncView,
)

app_name = "sync"

urlpatterns = [
    path("manifest.json", PwaManifestView.as_view(), name="pwa_manifest"),
    path("sw.js", ServiceWorkerView.as_view(), name="pwa_sw"),
    path("offline/", OfflineFallbackView.as_view(), name="pwa_offline"),
    path("api/sync/bootstrap/", OfflineBootstrapDataView.as_view(), name="sync_bootstrap"),
    path("api/sync/records/", OfflineRecordsSyncView.as_view(), name="sync_records"),
]

