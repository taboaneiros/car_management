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
    # Allauth (authentication)
    path("accounts/", include("allauth.urls")),
    # Apps
    path("", include("apps.dashboard.urls")),
    path("vehicles/", include("apps.vehicles.urls")),
    path("fuel/", include("apps.fuel.urls")),
    path("expenses/", include("apps.expenses.urls")),
    path("imports/", include("apps.imports.urls")),
    path("profile/", include("apps.users.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)