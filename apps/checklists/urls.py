"""
URL routes for the checklists app.
"""
from django.urls import path

from . import views

app_name = "checklists"

urlpatterns = [
    path("", views.ChecklistListView.as_view(), name="list"),
    path("create/", views.ChecklistCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.ChecklistDetailView.as_view(), name="detail"),
    path("<uuid:pk>/delete/", views.ChecklistDeleteView.as_view(), name="delete"),
]

