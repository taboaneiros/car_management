"""
URL configuration for the vehicles app.
"""
from django.urls import path

from . import views

app_name = "vehicles"

urlpatterns = [
    # Vehicle CRUD
    path("", views.VehicleListView.as_view(), name="list"),
    path("new/", views.VehicleCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.VehicleDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.VehicleUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.VehicleDeleteView.as_view(), name="delete"),
    path("<uuid:pk>/activate/", views.VehicleActivateView.as_view(), name="activate"),
]