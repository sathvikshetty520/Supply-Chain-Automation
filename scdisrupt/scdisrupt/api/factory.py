"""Factory and helper functions to build disruptions from API requests."""
from typing import Any, Dict
from scdisrupt.disruptions.base import Disruption
from scdisrupt.disruptions.catalog import (
    PortStrikeDisruption,
    SupplierFailureDisruption,
    DemandSurgeDisruption,
    CurrencyShockDisruption,
)


def create_disruption(disruption_type: str, parameters: Dict[str, Any]) -> Disruption:
    """Instantiate a Disruption object based on request type and parameters."""
    if disruption_type == "port_strike":
        lead_time_mult = float(parameters.get("lead_time_multiplier", 3.0))
        target_modes = parameters.get("target_modes", ["ocean"])
        return PortStrikeDisruption(lead_time_multiplier=lead_time_mult, target_modes=target_modes)

    elif disruption_type == "supplier_failure":
        supplier_id = str(parameters.get("supplier_id", "SUP_1"))
        offline_days = int(parameters.get("offline_days", 30))
        capacity_reduction = float(parameters.get("capacity_reduction", 1.0))
        return SupplierFailureDisruption(
            supplier_id=supplier_id,
            offline_days=offline_days,
            capacity_reduction=capacity_reduction,
        )

    elif disruption_type == "demand_surge":
        surge_factor = float(parameters.get("surge_factor", 1.40))
        target_customers = parameters.get("target_customers", None)
        return DemandSurgeDisruption(surge_factor=surge_factor, target_customers=target_customers)

    elif disruption_type == "currency_shock":
        cost_multiplier = float(parameters.get("cost_multiplier", 1.25))
        return CurrencyShockDisruption(cost_multiplier=cost_multiplier)

    else:
        raise ValueError(f"Unknown disruption type: {disruption_type}")
