"""
URL routes for the trips app.
"""
from django.urls import path

from . import views

app_name = "trips"

urlpatterns = [
    path("", views.TripListView.as_view(), name="list"),
    path("create/", views.TripCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.TripDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.TripUpdateView.as_view(), name="edit"),
    path("<uuid:pk>/delete/", views.TripDeleteView.as_view(), name="delete"),
]

