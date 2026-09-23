"""
Views for the expenses app.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django.utils.translation import gettext as _
from django.db import models
from apps.vehicles.models import Vehicle

from .forms import ExpenseCategoryForm, ExpenseForm
from .models import Expense, ExpenseCategory


class ExpenseListView(LoginRequiredMixin, ListView):
    """
    View for listing expenses.
    """

    model = Expense
    template_name = "expenses/expense_list.html"
    context_object_name = "expenses"
    paginate_by = 20

    def get_queryset(self):
        """Return expenses for the user's vehicles."""
        queryset = Expense.objects.filter(
            vehicle__owner_primary=self.request.user,
        ).select_related("vehicle", "category")

        vehicle_id = self.request.GET.get("vehicle")
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)

        category_id = self.request.GET.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")
        if start_date:
            queryset = queryset.filter(occurred_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(occurred_at__lte=end_date)

        return queryset.order_by("-occurred_at")

    def get_context_data(self, **kwargs):
        """Add vehicles and categories to context."""
        context = super().get_context_data(**kwargs)
        context["vehicles"] = Vehicle.objects.filter(
            owner_primary=self.request.user,
            is_active=True,
        )
        context["categories"] = ExpenseCategory.objects.filter(
            is_active=True,
        ).filter(
            models.Q(user=self.request.user) | models.Q(user__isnull=True),
        ).order_by("name")
        return context


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating a new expense.
    """

    model = Expense
    form_class = ExpenseForm
    template_name = "expenses/expense_form.html"
    success_url = reverse_lazy("expenses:list")

    def dispatch(self, request, *args, **kwargs):
        """Get the vehicle."""
        self.vehicle = None
        vehicle_id = kwargs.get("vehicle_id") or request.GET.get("vehicle")
        if vehicle_id:
            self.vehicle = get_object_or_404(
                Vehicle,
                id=vehicle_id,
                owner_primary=request.user,
                is_active=True,
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass vehicle and user to form."""
        kwargs = super().get_form_kwargs()
        kwargs["vehicle"] = self.vehicle
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Set the vehicle."""
        # Get vehicle from form (selected by user or passed via URL)
        vehicle = form.cleaned_data.get("vehicle")
        
        if not vehicle:
            messages.error(self.request, _("No vehicle specified."))
            return redirect("vehicles:list")

        # The vehicle is already set by the form since it's in fields
        # But we ensure it's set on the instance
        form.instance.vehicle = vehicle
        
        response = super().form_valid(form)

        if form.instance.odometer:
            vehicle.update_odometer_cache(form.instance.odometer)

        messages.success(self.request, "Despesa registrada com sucesso.")
        return response

    def get_context_data(self, **kwargs):
        """Add vehicle to context."""
        context = super().get_context_data(**kwargs)
        context["vehicle"] = self.vehicle
        return context


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """
    View for updating an expense.
    """

    model = Expense
    form_class = ExpenseForm
    template_name = "expenses/expense_form.html"
    success_url = reverse_lazy("expenses:list")

    def get_queryset(self):
        """Return only the user's expenses."""
        return Expense.objects.filter(
            vehicle__owner_primary=self.request.user,
        ).select_related("vehicle")

    def get_form_kwargs(self):
        """Pass vehicle and user to form."""
        kwargs = super().get_form_kwargs()
        kwargs["vehicle"] = self.object.vehicle
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        messages.success(self.request, "Despesa atualizada com sucesso.")
        return response


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    """
    View for deleting an expense.
    """

    model = Expense
    template_name = "expenses/expense_confirm_delete.html"
    success_url = reverse_lazy("expenses:list")

    def get_queryset(self):
        """Return only the user's expenses."""
        return Expense.objects.filter(
            vehicle__owner_primary=self.request.user,
        ).select_related("vehicle")

    def delete(self, request, *args, **kwargs):
        """Delete the expense."""
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, "Despesa removida com sucesso.")
        return redirect(self.success_url)


class ExpenseCategoryListView(LoginRequiredMixin, ListView):
    """
    View for listing expense categories.
    """

    model = ExpenseCategory
    template_name = "expenses/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        """Return categories for the user, including system categories."""
        return ExpenseCategory.objects.filter(
            is_active=True,
        ).filter(
            models.Q(user=self.request.user) | models.Q(user__isnull=True),
        ).order_by("name")


class ExpenseCategoryCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating a new expense category.
    """

    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = "expenses/category_form.html"
    success_url = reverse_lazy("expenses:category_list")

    def form_valid(self, form):
        """Set the user."""
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Categoria criada com sucesso.")
        return response