"""Factory and helper functions to build disruptions from API requests."""
from typing import Any, Dict
from scdisrupt.disruptions.base import Disruption
from scdisrupt.disruptions.catalog import (
    PortStrikeDisruption,
    SupplierFailureDisruption,
    DemandSurgeDisruption,
    CurrencyShockDisruption,
    CyberattackDisruption,
    CanalBlockageDisruption,
    RawMaterialExportBanDisruption,
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
        return DemandSurgeDisruption(surge_factor=surge_factor, customer_ids=target_customers)

    elif disruption_type == "currency_shock":
        cost_multiplier = float(parameters.get("cost_multiplier", 1.25))
        return CurrencyShockDisruption(cost_multiplier=cost_multiplier)

    elif disruption_type == "cyberattack":
        target_node = str(parameters.get("target_node_id", "FAC_1"))
        throughput_red = float(parameters.get("throughput_reduction", 0.85))
        duration = int(parameters.get("duration_days", 21))
        return CyberattackDisruption(
            target_node_id=target_node,
            throughput_reduction=throughput_red,
            duration_days=duration,
        )

    elif disruption_type == "canal_blockage":
        lead_time_mult = float(parameters.get("lead_time_multiplier", 4.0))
        cost_mult = float(parameters.get("cost_multiplier", 1.60))
        affected_modes = parameters.get("affected_modes", ["ocean"])
        return CanalBlockageDisruption(
            lead_time_multiplier=lead_time_mult,
            cost_multiplier=cost_mult,
            affected_modes=affected_modes,
        )

    elif disruption_type == "raw_material_ban":
        supplier_ids = parameters.get("supplier_ids", ["SUP_1"])
        capacity_curtailment = float(parameters.get("capacity_curtailment", 0.90))
        tariff_surcharge = float(parameters.get("tariff_surcharge", 1.75))
        return RawMaterialExportBanDisruption(
            supplier_ids=supplier_ids,
            capacity_curtailment=capacity_curtailment,
            tariff_surcharge=tariff_surcharge,
        )

    else:
        raise ValueError(f"Unknown disruption type: {disruption_type}")
