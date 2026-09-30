"""
URLs for the maintenance app.
"""
from django.urls import path

from . import views

app_name = "maintenance"

urlpatterns = [
    # Maintenance records
    path("", views.MaintenanceListView.as_view(), name="list"),
    path("create/", views.MaintenanceCreateView.as_view(), name="create"),
    path(
        "create/<uuid:vehicle_id>/",
        views.MaintenanceCreateView.as_view(),
        name="create_for_vehicle",
    ),
    path(
        "<uuid:pk>/",
        views.MaintenanceDetailView.as_view(),
        name="detail",
    ),
    path(
        "<uuid:pk>/edit/",
        views.MaintenanceUpdateView.as_view(),
        name="update",
    ),
    path(
        "<uuid:pk>/delete/",
        views.MaintenanceDeleteView.as_view(),
        name="delete",
    ),
    # Service Types
    path(
        "service-types/",
        views.ServiceTypeListView.as_view(),
        name="service_type_list",
    ),
    path(
        "service-types/create/",
        views.ServiceTypeCreateView.as_view(),
        name="service_type_create",
    ),
    path(
        "service-types/<uuid:pk>/edit/",
        views.ServiceTypeUpdateView.as_view(),
        name="service_type_update",
    ),
]

