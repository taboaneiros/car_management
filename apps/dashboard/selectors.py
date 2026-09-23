"""
Dashboard selectors for aggregating data.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Avg
from django.utils import timezone

from apps.fuel.models import Refueling
from apps.expenses.models import Expense
from apps.vehicles.models import Vehicle


class DashboardSelectors:
    """
    Selectors for dashboard data aggregation.
    """

    @staticmethod
    def get_month_summary(user, vehicle=None):
        """
        Get summary for the current month.
        
        Args:
            user: The user to get summary for
            vehicle: Optional vehicle to filter by
        
        Returns:
            dict with fuel_total, expenses_total, total_spent, refuelings_count, expenses_count
        """
        today = timezone.now().date()
        start_of_month = today.replace(day=1)

        # Base filters
        fuel_filter = {
            "vehicle__owner_primary": user,
            "occurred_at__gte": start_of_month,
            "occurred_at__lte": today,
        }
        expense_filter = {
            "vehicle__owner_primary": user,
            "occurred_at__gte": start_of_month,
            "occurred_at__lte": today,
        }

        if vehicle:
            fuel_filter["vehicle"] = vehicle
            expense_filter["vehicle"] = vehicle

        # Fuel totals
        fuel_agg = Refueling.objects.filter(**fuel_filter).aggregate(
            total=Sum("total_amount"),
            count=Count("id"),
            total_liters=Sum("liters"),
        )

        # Expense totals
        expense_agg = Expense.objects.filter(**expense_filter).aggregate(
            total=Sum("amount"),
            count=Count("id"),
        )

        fuel_total = fuel_agg["total"] or Decimal("0")
        expenses_total = expense_agg["total"] or Decimal("0")

        return {
            "fuel_total": fuel_total,
            "expenses_total": expenses_total,
            "total_spent": fuel_total + expenses_total,
            "refuelings_count": fuel_agg["count"] or 0,
            "expenses_count": expense_agg["count"] or 0,
            "total_liters": fuel_agg["total_liters"] or Decimal("0"),
        }

    @staticmethod
    def get_year_summary(user, vehicle=None):
        """
        Get summary for the current year.
        
        Args:
            user: The user to get summary for
            vehicle: Optional vehicle to filter by
        
        Returns:
            dict with fuel_total, expenses_total, total_spent
        """
        today = timezone.now().date()
        start_of_year = today.replace(month=1, day=1)

        fuel_filter = {
            "vehicle__owner_primary": user,
            "occurred_at__gte": start_of_year,
            "occurred_at__lte": today,
        }
        expense_filter = {
            "vehicle__owner_primary": user,
            "occurred_at__gte": start_of_year,
            "occurred_at__lte": today,
        }

        if vehicle:
            fuel_filter["vehicle"] = vehicle
            expense_filter["vehicle"] = vehicle

        fuel_total = Refueling.objects.filter(**fuel_filter).aggregate(
            total=Sum("total_amount"),
        )["total"] or Decimal("0")

        expenses_total = Expense.objects.filter(**expense_filter).aggregate(
            total=Sum("amount"),
        )["total"] or Decimal("0")

        return {
            "fuel_total": fuel_total,
            "expenses_total": expenses_total,
            "total_spent": fuel_total + expenses_total,
        }

    @staticmethod
    def get_recent_refuelings(user, limit=5, vehicle=None):
        """
        Get recent refuelings for the user.
        
        Args:
            user: The user to get refuelings for
            limit: Maximum number of refuelings to return
            vehicle: Optional vehicle to filter by
        
        Returns:
            QuerySet of Refueling objects
        """
        queryset = Refueling.objects.filter(
            vehicle__owner_primary=user,
        ).select_related("vehicle", "fuel_type")

        if vehicle:
            queryset = queryset.filter(vehicle=vehicle)

        return queryset.order_by("-occurred_at", "-created_at")[:limit]

    @staticmethod
    def get_recent_expenses(user, limit=5, vehicle=None):
        """
        Get recent expenses for the user.
        
        Args:
            user: The user to get expenses for
            limit: Maximum number of expenses to return
            vehicle: Optional vehicle to filter by
        
        Returns:
            QuerySet of Expense objects
        """
        queryset = Expense.objects.filter(
            vehicle__owner_primary=user,
        ).select_related("vehicle", "category")

        if vehicle:
            queryset = queryset.filter(vehicle=vehicle)

        return queryset.order_by("-occurred_at", "-created_at")[:limit]

    @staticmethod
    def get_vehicle_stats(vehicle):
        """
        Get statistics for a specific vehicle.
        
        Args:
            vehicle: The Vehicle instance
        
        Returns:
            dict with odometer, avg_consumption, total_fuel_cost, total_expenses
        """
        # Fuel stats
        fuel_stats = Refueling.objects.filter(vehicle=vehicle).aggregate(
            total_cost=Sum("total_amount"),
            total_liters=Sum("liters"),
            avg_consumption=Avg("consumption_km_l"),
            count=Count("id"),
        )

        # Expense stats
        expense_stats = Expense.objects.filter(vehicle=vehicle).aggregate(
            total=Sum("amount"),
            count=Count("id"),
        )

        return {
            "odometer": vehicle.current_odometer_cache,
            "avg_consumption": fuel_stats["avg_consumption"],
            "total_fuel_cost": fuel_stats["total_cost"] or Decimal("0"),
            "total_expenses": expense_stats["total"] or Decimal("0"),
            "refuelings_count": fuel_stats["count"] or 0,
            "expenses_count": expense_stats["count"] or 0,
        }

    @staticmethod
    def get_monthly_costs_chart_data(user, months=6, vehicle=None):
        """
        Get data for monthly costs chart.
        
        Args:
            user: The user to get data for
            months: Number of months to include
            vehicle: Optional vehicle to filter by
        
        Returns:
            list of dicts with month, fuel, expenses
        """
        today = timezone.now().date()
        data = []

        for i in range(months - 1, -1, -1):
            month_date = today - timedelta(days=i * 30)
            month_start = month_date.replace(day=1)
            
            # Get last day of month
            if month_date.month == 12:
                month_end = month_date.replace(day=31)
            else:
                next_month = month_date.replace(month=month_date.month + 1, day=1)
                month_end = next_month - timedelta(days=1)

            fuel_filter = {
                "vehicle__owner_primary": user,
                "occurred_at__gte": month_start,
                "occurred_at__lte": month_end,
            }
            expense_filter = {
                "vehicle__owner_primary": user,
                "occurred_at__gte": month_start,
                "occurred_at__lte": month_end,
            }

            if vehicle:
                fuel_filter["vehicle"] = vehicle
                expense_filter["vehicle"] = vehicle

            fuel_total = Refueling.objects.filter(**fuel_filter).aggregate(
                total=Sum("total_amount"),
            )["total"] or Decimal("0")

            expenses_total = Expense.objects.filter(**expense_filter).aggregate(
                total=Sum("amount"),
            )["total"] or Decimal("0")

            data.append({
                "month": month_start.strftime("%b/%y"),
                "fuel": float(fuel_total),
                "expenses": float(expenses_total),
                "total": float(fuel_total + expenses_total),
            })

        return data

    @staticmethod
    def get_expense_categories_breakdown(user, vehicle=None):
        """
        Get expense breakdown by category.
        
        Args:
            user: The user to get data for
            vehicle: Optional vehicle to filter by
        
        Returns:
            list of dicts with category, total, percentage
        """
        filters = {"vehicle__owner_primary": user}
        if vehicle:
            filters["vehicle"] = vehicle

        expenses = Expense.objects.filter(**filters).values(
            "category__name",
        ).annotate(
            total=Sum("amount"),
        ).order_by("-total")

        total_amount = sum(e["total"] or Decimal("0") for e in expenses)

        result = []
        for expense in expenses:
            category_name = expense["category__name"] or "Sem categoria"
            amount = expense["total"] or Decimal("0")
            percentage = (amount / total_amount * 100) if total_amount > 0 else 0

            result.append({
                "category": category_name,
                "total": float(amount),
                "percentage": round(float(percentage), 1),
            })

        return result