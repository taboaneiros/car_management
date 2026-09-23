"""
URL configuration for the users app.
"""
from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    # Profile
    path("", views.ProfileDetailView.as_view(), name="profile"),
    path("edit/", views.ProfileUpdateView.as_view(), name="profile_edit"),
    path("delete-account/", views.AccountDeleteView.as_view(), name="account_delete"),
]