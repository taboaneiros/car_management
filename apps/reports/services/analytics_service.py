"""
Analytics and vehicle comparison service for advanced reporting.
"""
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from django.db.models import Avg, Count, Max, Min, Sum
from django.utils import timezone

from apps.expenses.models import Expense
from apps.fuel.models import Refueling
from apps.maintenance.models import Maintenance
from apps.trips.models import Trip
from apps.vehicles.models import Vehicle


class VehicleComparisonService:
    """Computes comparison metrics, TCO and efficiency benchmarks."""

    @classmethod
    def get_comparison_data(
        cls,
        user,
        vehicle_ids: Optional[List[str]] = None,
        date_start=None,
        date_end=None,
    ) -> Dict:
        """
        Gathers comparison metrics for user's vehicles.
        """
        vehicles_qs = Vehicle.objects.filter(owner_primary=user, is_active=True)
        if vehicle_ids:
            vehicles_qs = vehicles_qs.filter(id__in=vehicle_ids)

        vehicles_data = []

        for v in vehicles_qs:
            # Filters
            f_filter = {"vehicle": v}
            e_filter = {"vehicle": v}
            m_filter = {"vehicle": v}
            t_filter = {"vehicle": v}

            if date_start:
                f_filter["occurred_at__gte"] = date_start
                e_filter["occurred_at__gte"] = date_start
                m_filter["occurred_at__gte"] = date_start
                t_filter["started_at__date__gte"] = date_start

            if date_end:
                f_filter["occurred_at__lte"] = date_end
                e_filter["occurred_at__lte"] = date_end
                m_filter["occurred_at__lte"] = date_end
                t_filter["started_at__date__lte"] = date_end

            # Aggregations
            fuel_agg = Refueling.objects.filter(**f_filter).aggregate(
                total_cost=Sum("total_amount"),
                total_liters=Sum("liters"),
                avg_km_l=Avg("consumption_km_l"),
                min_odo=Min("odometer"),
                max_odo=Max("odometer"),
                count=Count("id"),
            )

            exp_agg = Expense.objects.filter(**e_filter).aggregate(
                total_cost=Sum("amount"),
                count=Count("id"),
            )

            maint_agg = Maintenance.objects.filter(**m_filter).aggregate(
                total_cost=Sum("total_amount"),
                count=Count("id"),
            )

            trip_agg = Trip.objects.filter(**t_filter).aggregate(
                total_km=Sum("distance"),
                count=Count("id"),
            )

            fuel_cost = fuel_agg["total_cost"] or Decimal("0")
            exp_cost = exp_agg["total_cost"] or Decimal("0")
            maint_cost = maint_agg["total_cost"] or Decimal("0")
            total_tco = fuel_cost + exp_cost + maint_cost

            # Distance calculation: odometer range from refuelings or trips distance
            odo_diff = 0
            if fuel_agg["max_odo"] and fuel_agg["min_odo"]:
                odo_diff = fuel_agg["max_odo"] - fuel_agg["min_odo"]

            trip_km = int(trip_agg["total_km"] or 0)
            distance_driven = max(odo_diff, trip_km)

            # Cost per km
            cost_per_km = (
                (total_tco / Decimal(str(distance_driven))).quantize(Decimal("0.01"))
                if distance_driven > 0
                else Decimal("0")
            )
            fuel_per_km = (
                (fuel_cost / Decimal(str(distance_driven))).quantize(Decimal("0.01"))
                if distance_driven > 0
                else Decimal("0")
            )
            maint_per_km = (
                (maint_cost / Decimal(str(distance_driven))).quantize(Decimal("0.01"))
                if distance_driven > 0
                else Decimal("0")
            )

            avg_consumption = (
                round(float(fuel_agg["avg_km_l"]), 2)
                if fuel_agg["avg_km_l"] is not None
                else 0.0
            )

            vehicles_data.append({
                "vehicle": v,
                "distance_km": distance_driven,
                "fuel_cost": fuel_cost,
                "fuel_liters": fuel_agg["total_liters"] or Decimal("0"),
                "avg_consumption": avg_consumption,
                "refuelings_count": fuel_agg["count"],
                "maintenance_cost": maint_cost,
                "maintenances_count": maint_agg["count"],
                "expense_cost": exp_cost,
                "expenses_count": exp_agg["count"],
                "total_tco": total_tco,
                "cost_per_km": cost_per_km,
                "fuel_per_km": fuel_per_km,
                "maint_per_km": maint_per_km,
                "trips_count": trip_agg["count"],
            })

        # Determine best performers if multiple vehicles
        best_consumption_v = None
        lowest_cost_km_v = None

        valid_consumption = [v for v in vehicles_data if v["avg_consumption"] > 0]
        if valid_consumption:
            best_consumption_v = max(valid_consumption, key=lambda x: x["avg_consumption"])

        valid_cost_km = [v for v in vehicles_data if v["cost_per_km"] > 0]
        if valid_cost_km:
            lowest_cost_km_v = min(valid_cost_km, key=lambda x: x["cost_per_km"])

        return {
            "vehicles_data": vehicles_data,
            "best_consumption": best_consumption_v,
            "lowest_cost_km": lowest_cost_km_v,
        }

    @classmethod
    def get_monthly_consumption_trend(cls, user, vehicle=None, months: int = 6) -> List[Dict]:
        """
        Returns average consumption (km/l) per month for the last `months` months.
        """
        today = timezone.now().date()
        result = []

        for i in range(months - 1, -1, -1):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1

            # First and last day of month
            start_date = timezone.datetime(year, month, 1).date()
            if month == 12:
                end_date = timezone.datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = timezone.datetime(year, month + 1, 1).date() - timedelta(days=1)

            qs = Refueling.objects.filter(
                vehicle__owner_primary=user,
                occurred_at__gte=start_date,
                occurred_at__lte=end_date,
                consumption_km_l__isnull=False,
            )
            if vehicle:
                qs = qs.filter(vehicle=vehicle)

            avg_km_l = qs.aggregate(avg=Avg("consumption_km_l"))["avg"]
            month_label = start_date.strftime("%b/%y")

            result.append({
                "label": month_label,
                "avg_km_l": round(float(avg_km_l), 2) if avg_km_l else 0.0,
            })

        return result

    @classmethod
    def get_monthly_fuel_analytics(cls, user, vehicle=None, months: int = 6) -> Dict:
        """
        Returns monthly fueling analytics: cost over time, fuel price per liter over time,
        and consumption trend.
        """
        today = timezone.now().date()
        months_data = []

        total_spend_all = Decimal("0")
        total_liters_all = Decimal("0")
        all_prices = []

        for i in range(months - 1, -1, -1):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1

            start_date = timezone.datetime(year, month, 1).date()
            if month == 12:
                end_date = timezone.datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = timezone.datetime(year, month + 1, 1).date() - timedelta(days=1)

            qs = Refueling.objects.filter(
                vehicle__owner_primary=user,
                occurred_at__gte=start_date,
                occurred_at__lte=end_date,
            )
            if vehicle:
                qs = qs.filter(vehicle=vehicle)

            agg = qs.aggregate(
                total_cost=Sum("total_amount"),
                total_liters=Sum("liters"),
                avg_price=Avg("price_per_liter"),
                avg_km_l=Avg("consumption_km_l"),
                count=Count("id"),
            )

            cost = float(agg["total_cost"] or 0)
            liters = float(agg["total_liters"] or 0)
            avg_price = float(agg["avg_price"] or 0)
            avg_km_l = float(agg["avg_km_l"] or 0)

            total_spend_all += agg["total_cost"] or Decimal("0")
            total_liters_all += agg["total_liters"] or Decimal("0")
            if avg_price > 0:
                all_prices.append(avg_price)

            months_data.append({
                "label": start_date.strftime("%b/%y"),
                "cost": round(cost, 2),
                "liters": round(liters, 2),
                "avg_price": round(avg_price, 3),
                "avg_km_l": round(avg_km_l, 2),
                "count": agg["count"],
            })

        overall_avg_price = (
            round(sum(all_prices) / len(all_prices), 3) if all_prices else 0.0
        )

        return {
            "labels": [m["label"] for m in months_data],
            "costs": [m["cost"] for m in months_data],
            "prices": [m["avg_price"] for m in months_data],
            "km_l": [m["avg_km_l"] for m in months_data],
            "liters": [m["liters"] for m in months_data],
            "total_spend": total_spend_all,
            "total_liters": total_liters_all,
            "overall_avg_price": overall_avg_price,
            "months_data": months_data,
        }

    @classmethod
    def get_expense_analytics(cls, user, vehicle=None, months: int = 6) -> Dict:
        """
        Returns expense breakdown by category and monthly evolution.
        """
        today = timezone.now().date()
        months_data = []
        total_spend = Decimal("0")

        for i in range(months - 1, -1, -1):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1

            start_date = timezone.datetime(year, month, 1).date()
            if month == 12:
                end_date = timezone.datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = timezone.datetime(year, month + 1, 1).date() - timedelta(days=1)

            qs = Expense.objects.filter(
                vehicle__owner_primary=user,
                occurred_at__gte=start_date,
                occurred_at__lte=end_date,
            )
            if vehicle:
                qs = qs.filter(vehicle=vehicle)

            agg = qs.aggregate(total=Sum("amount"))
            cost = float(agg["total"] or 0)
            total_spend += agg["total"] or Decimal("0")

            months_data.append({
                "label": start_date.strftime("%b/%y"),
                "cost": round(cost, 2),
            })

        # Category breakdown
        cat_qs = Expense.objects.filter(vehicle__owner_primary=user)
        if vehicle:
            cat_qs = cat_qs.filter(vehicle=vehicle)

        cat_agg = (
            cat_qs.values("category__name")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        cat_labels = []
        cat_values = []
        for item in cat_agg:
            name = item["category__name"] or "Geral"
            cat_labels.append(name)
            cat_values.append(float(item["total"] or 0))

        return {
            "months_labels": [m["label"] for m in months_data],
            "months_costs": [m["cost"] for m in months_data],
            "cat_labels": cat_labels,
            "cat_values": cat_values,
            "total_spend": total_spend,
        }

    @classmethod
    def get_maintenance_analytics(cls, user, vehicle=None, months: int = 6) -> Dict:
        """
        Returns maintenance breakdown: preventive vs corrective, service types, and monthly evolution.
        """
        today = timezone.now().date()
        months_data = []
        total_spend = Decimal("0")

        for i in range(months - 1, -1, -1):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1

            start_date = timezone.datetime(year, month, 1).date()
            if month == 12:
                end_date = timezone.datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = timezone.datetime(year, month + 1, 1).date() - timedelta(days=1)

            qs = Maintenance.objects.filter(
                vehicle__owner_primary=user,
                occurred_at__gte=start_date,
                occurred_at__lte=end_date,
            )
            if vehicle:
                qs = qs.filter(vehicle=vehicle)

            agg = qs.aggregate(total=Sum("total_amount"))
            cost = float(agg["total"] or 0)
            total_spend += agg["total"] or Decimal("0")

            months_data.append({
                "label": start_date.strftime("%b/%y"),
                "cost": round(cost, 2),
            })

        maint_qs = Maintenance.objects.filter(vehicle__owner_primary=user)
        if vehicle:
            maint_qs = maint_qs.filter(vehicle=vehicle)

        # Preventive vs Corrective
        type_agg = maint_qs.values("maintenance_type").annotate(
            total=Sum("total_amount"), count=Count("id")
        )
        type_map = {item["maintenance_type"]: float(item["total"] or 0) for item in type_agg}
        preventive_cost = type_map.get("preventive", 0.0)
        corrective_cost = type_map.get("corrective", 0.0)

        # Service Types
        service_agg = (
            maint_qs.values("service_type__name")
            .annotate(total=Sum("total_amount"), count=Count("id"))
            .order_by("-total")[:8]
        )
        service_labels = []
        service_values = []
        for item in service_agg:
            name = item["service_type__name"] or "Outros Serviços"
            service_labels.append(name)
            service_values.append(float(item["total"] or 0))

        return {
            "months_labels": [m["label"] for m in months_data],
            "months_costs": [m["cost"] for m in months_data],
            "preventive_cost": preventive_cost,
            "corrective_cost": corrective_cost,
            "service_labels": service_labels,
            "service_values": service_values,
            "total_spend": total_spend,
        }

