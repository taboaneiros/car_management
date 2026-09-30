"""
URL configuration for car_management project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Internationalization language switch
    path("i18n/", include("django.conf.urls.i18n")),
    # Allauth (authentication)
    path("accounts/", include("allauth.urls")),
    # Apps
    path("", include("apps.dashboard.urls")),
    path("vehicles/", include("apps.vehicles.urls")),
    path("fuel/", include("apps.fuel.urls")),
    path("expenses/", include("apps.expenses.urls")),
    path("maintenance/", include("apps.maintenance.urls")),
    path("reminders/", include("apps.reminders.urls")),
    path("trips/", include("apps.trips.urls")),
    path("checklists/", include("apps.checklists.urls")),
    path("reports/", include("apps.reports.urls")),
    path("imports/", include("apps.imports.urls")),
    path("profile/", include("apps.users.urls")),
    path("", include("apps.sync.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)