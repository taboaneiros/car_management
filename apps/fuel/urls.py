"""
URL configuration for the fuel app.
"""
from django.urls import path

from . import views

app_name = "fuel"

urlpatterns = [
    # Refueling CRUD
    path("", views.RefuelingListView.as_view(), name="list"),
    path("new/", views.RefuelingCreateView.as_view(), name="create"),
    path("<uuid:pk>/edit/", views.RefuelingUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.RefuelingDeleteView.as_view(), name="delete"),
    # HTMX partials
    path("partials/list/", views.RefuelingListPartialView.as_view(), name="list_partial"),
]