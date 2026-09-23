"""
Fuel consumption calculators.
Implements the calculation logic for fuel consumption between full tank refuelings.
"""
from decimal import Decimal, DivisionByZero, InvalidOperation

from django.db.models import Q


class ConsumptionCalculator:
    """
    Calculator for fuel consumption metrics.
    
    The consumption is calculated between two full tank refuelings:
    - The distance traveled is the difference in odometer readings
    - The fuel used is the liters from the second refueling
    - Consumption = distance / liters
    """

    @staticmethod
    def calculate_consumption(refueling, previous_full_tank=None):
        """
        Calculate consumption for a refueling.
        
        Args:
            refueling: The Refueling instance to calculate for
            previous_full_tank: The previous full tank refueling (optional, will be fetched if not provided)
        
        Returns:
            dict with consumption_km_l, distance_since_last_full, cost_per_km
        """
        result = {
            "consumption_km_l": None,
            "distance_since_last_full": None,
            "cost_per_km": None,
        }

        # Only calculate for full tank refuelings
        if not refueling.is_full_tank:
            return result

        # Skip if missed previous fillup
        if refueling.missed_previous_fillup:
            return result

        # Get previous full tank if not provided
        if previous_full_tank is None:
            previous_full_tank = (
                refueling.__class__.objects.filter(
                    vehicle=refueling.vehicle,
                    is_full_tank=True,
                    missed_previous_fillup=False,
                )
                .filter(
                    Q(occurred_at__lt=refueling.occurred_at)
                    | Q(occurred_at=refueling.occurred_at, odometer__lt=refueling.odometer)
                )
                .order_by("-occurred_at", "-odometer")
                .first()
            )

        if previous_full_tank is None:
            return result

        # Calculate distance
        distance = refueling.odometer - previous_full_tank.odometer
        if distance <= 0:
            return result

        result["distance_since_last_full"] = distance

        # Calculate consumption (km/l)
        try:
            liters = Decimal(str(refueling.liters))
            if liters > 0:
                consumption = Decimal(distance) / liters
                result["consumption_km_l"] = consumption.quantize(Decimal("0.01"))
        except (DivisionByOne, InvalidOperation, ValueError):
            pass

        # Calculate cost per km
        try:
            total_amount = Decimal(str(refueling.total_amount))
            if total_amount > 0 and distance > 0:
                cost_per_km = total_amount / Decimal(distance)
                result["cost_per_km"] = cost_per_km.quantize(Decimal("0.0001"))
        except (DivisionByOne, InvalidOperation, ValueError):
            pass

        return result

    @staticmethod
    def update_refueling_consumption(refueling, save=True):
        """
        Update the consumption fields for a refueling.
        
        Args:
            refueling: The Refueling instance to update
            save: Whether to save the refueling after updating
        
        Returns:
            The updated refueling
        """
        result = ConsumptionCalculator.calculate_consumption(refueling)

        refueling.consumption_km_l = result["consumption_km_l"]
        refueling.distance_since_last_full = result["distance_since_last_full"]
        refueling.cost_per_km = result["cost_per_km"]

        if save:
            refueling.save(
                update_fields=[
                    "consumption_km_l",
                    "distance_since_last_full",
                    "cost_per_km",
                    "updated_at",
                ]
            )

        return refueling

    @staticmethod
    def recalculate_vehicle_consumption(vehicle):
        """
        Recalculate consumption for all refuelings of a vehicle.
        This is useful when a refueling is deleted or updated.
        
        Args:
            vehicle: The Vehicle instance
        """
        from .models import Refueling

        refuelings = Refueling.objects.filter(
            vehicle=vehicle,
            is_full_tank=True,
        ).order_by("occurred_at", "odometer")

        previous = None
        for refueling in refuelings:
            if refueling.missed_previous_fillup:
                previous = refueling
                continue

            if previous is not None:
                ConsumptionCalculator.update_refueling_consumption(refueling)
            previous = refueling

    @staticmethod
    def detect_outliers(vehicle, threshold=2.0):
        """
        Detect consumption outliers for a vehicle.
        An outlier is a consumption that deviates more than threshold standard deviations
        from the mean.
        
        Args:
            vehicle: The Vehicle instance
            threshold: Number of standard deviations to consider as outlier
        
        Returns:
            List of outlier refueling IDs
        """
        from .models import Refueling
        import statistics

        refuelings = Refueling.objects.filter(
            vehicle=vehicle,
            is_full_tank=True,
            consumption_km_l__isnull=False,
        ).values_list("id", "consumption_km_l")

        if len(refuelings) < 3:
            return []

        consumptions = [float(r[1]) for r in refuelings]
        mean = statistics.mean(consumptions)
        stdev = statistics.stdev(consumptions)

        if stdev == 0:
            return []

        outliers = []
        for refueling_id, consumption in refuelings:
            deviation = abs(float(consumption) - mean) / stdev
            if deviation > threshold:
                outliers.append(refueling_id)

        # Update outlier flags
        Refueling.objects.filter(vehicle=vehicle).update(is_outlier=False)
        Refueling.objects.filter(id__in=outliers).update(is_outlier=True)

        return outliers

    @staticmethod
    def get_average_consumption(vehicle, days=30):
        """
        Get average consumption for a vehicle over a period.
        
        Args:
            vehicle: The Vehicle instance
            days: Number of days to consider
        
        Returns:
            dict with average_consumption, total_distance, total_liters, total_cost
        """
        from datetime import timedelta
        from django.utils import timezone
        from .models import Refueling

        start_date = timezone.now().date() - timedelta(days=days)

        refuelings = Refueling.objects.filter(
            vehicle=vehicle,
            is_full_tank=True,
            occurred_at__gte=start_date,
            consumption_km_l__isnull=False,
        )

        if not refuelings.exists():
            return {
                "average_consumption": None,
                "total_distance": 0,
                "total_liters": Decimal("0"),
                "total_cost": Decimal("0"),
            }

        total_distance = sum(r.distance_since_last_full or 0 for r in refuelings)
        total_liters = sum(r.liters for r in refuelings)
        total_cost = sum(r.total_amount for r in refuelings)

        average_consumption = None
        if total_liters > 0 and total_distance > 0:
            average_consumption = Decimal(total_distance) / total_liters
            average_consumption = average_consumption.quantize(Decimal("0.01"))

        return {
            "average_consumption": average_consumption,
            "total_distance": total_distance,
            "total_liters": total_liters,
            "total_cost": total_cost,
        }