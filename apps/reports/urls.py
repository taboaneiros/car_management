"""
URL routes for the reports app.
"""
from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportsHubView.as_view(), name="hub"),
    path("comparison/", views.VehicleComparisonView.as_view(), name="comparison"),
    path("export/", views.ExportDataView.as_view(), name="export"),
    path("export/data/", views.ExportDataView.as_view(), name="export_data"),
    path("export/<str:entity>/", views.QuickExportView.as_view(), name="quick_export"),
    path("print/", views.PrintReportView.as_view(), name="print"),
    path("print/report/", views.PrintReportView.as_view(), name="print_report"),
]
