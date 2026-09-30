"""
URLs for the reminders app.
"""
from django.urls import path

from . import views

app_name = "reminders"

urlpatterns = [
    path("", views.ReminderListView.as_view(), name="list"),
    path("create/", views.ReminderCreateView.as_view(), name="create"),
    path(
        "create/<uuid:vehicle_id>/",
        views.ReminderCreateView.as_view(),
        name="create_for_vehicle",
    ),
    path(
        "<uuid:pk>/edit/",
        views.ReminderUpdateView.as_view(),
        name="update",
    ),
    path(
        "<uuid:pk>/delete/",
        views.ReminderDeleteView.as_view(),
        name="delete",
    ),
    path(
        "<uuid:pk>/complete/",
        views.ReminderCompleteView.as_view(),
        name="complete",
    ),
]

