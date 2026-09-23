"""
URL configuration for the expenses app.
"""
from django.urls import path

from . import views

app_name = "expenses"

urlpatterns = [
    # Expense CRUD
    path("", views.ExpenseListView.as_view(), name="list"),
    path("new/", views.ExpenseCreateView.as_view(), name="create"),
    path("<uuid:pk>/edit/", views.ExpenseUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.ExpenseDeleteView.as_view(), name="delete"),
    # Categories
    path("categories/", views.ExpenseCategoryListView.as_view(), name="category_list"),
    path("categories/new/", views.ExpenseCategoryCreateView.as_view(), name="category_create"),
    # Export
    # path("export/", views.export_expenses_csv, name="export_expenses_csv"),
]