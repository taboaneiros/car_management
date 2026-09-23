"""
URL configuration for the imports app.
"""
from django.urls import path

from . import views

app_name = "imports"

urlpatterns = [
    path("drivvo/", views.import_drivvo, name="import_drivvo"),
]
