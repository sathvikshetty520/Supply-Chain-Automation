"""Catalog of standard disruptions: supplier failure, port strike, currency shock, demand surge."""
from typing import List, Optional
import networkx as nx

from scdisrupt.disruptions.base import Disruption
from scdisrupt.twin.state import fork_graph


class SupplierFailureDisruption(Disruption):
    """Takes a supplier completely or partially offline for a specified number of days or permanently."""

    def __init__(self, supplier_id: str = "SUP_1", offline_days: int = 30, capacity_reduction: float = 1.0):
        super().__init__(
            name="Supplier Failure",
            description=f"Supplier {supplier_id} experiences outage ({int(capacity_reduction*100)}% capacity reduction)",
            parameters={"supplier_id": supplier_id, "offline_days": offline_days, "capacity_reduction": capacity_reduction},
        )
        self.supplier_id = supplier_id
        self.offline_days = offline_days
        self.capacity_reduction = capacity_reduction

    def apply(self, graph: nx.DiGraph) -> nx.DiGraph:
        g = fork_graph(graph)
        if self.supplier_id in g.nodes:
            orig_cap = g.nodes[self.supplier_id].get("daily_capacity", 100.0)
            g.nodes[self.supplier_id]["daily_capacity"] = max(0.0, orig_cap * (1.0 - self.capacity_reduction))
            if self.capacity_reduction >= 1.0:
                g.nodes[self.supplier_id]["operational"] = False
        return g


class PortStrikeDisruption(Disruption):
    """Simulates a major maritime port strike or bottleneck, drastically increasing lead times on ocean lanes."""

    def __init__(self, lead_time_multiplier: float = 3.0, target_modes: Optional[List[str]] = None):
        target_modes = target_modes or ["ocean"]
        super().__init__(
            name="Port Strike / Chokepoint",
            description=f"Port strike increases lead time by {lead_time_multiplier}x on {target_modes} lanes",
            parameters={"lead_time_multiplier": lead_time_multiplier, "target_modes": target_modes},
        )
        self.lead_time_multiplier = lead_time_multiplier
        self.target_modes = target_modes

    def apply(self, graph: nx.DiGraph) -> nx.DiGraph:
        g = fork_graph(graph)
        for u, v, attrs in g.edges(data=True):
            if attrs.get("mode") in self.target_modes:
                attrs["lead_time_multiplier"] = attrs.get("lead_time_multiplier", 1.0) * self.lead_time_multiplier
                attrs["disrupted"] = True
        return g


class CurrencyShockDisruption(Disruption):
    """Simulates an FX devaluation or fuel surcharge shock, inflating unit procurement and transport costs."""

    def __init__(self, cost_multiplier: float = 1.20):
        super().__init__(
            name="Currency & Fuel Shock",
            description=f"Cost inflation shock increases costs across the network by {int((cost_multiplier-1.0)*100)}%",
            parameters={"cost_multiplier": cost_multiplier},
        )
        self.cost_multiplier = cost_multiplier

    def apply(self, graph: nx.DiGraph) -> nx.DiGraph:
        g = fork_graph(graph)
        # Inflate supplier unit cost
        for n, attrs in g.nodes(data=True):
            if "unit_cost" in attrs:
                attrs["unit_cost"] *= self.cost_multiplier
        # Inflate lane transit cost
        for u, v, attrs in g.edges(data=True):
            attrs["cost_multiplier"] = attrs.get("cost_multiplier", 1.0) * self.cost_multiplier
        return g


class DemandSurgeDisruption(Disruption):
    """Simulates an unexpected market demand surge (e.g. +40%) across all or selected customer nodes."""

    def __init__(self, surge_factor: float = 1.40, customer_ids: Optional[List[str]] = None):
        super().__init__(
            name="Demand Surge",
            description=f"Customer demand surges by {int((surge_factor-1.0)*100)}%",
            parameters={"surge_factor": surge_factor, "customer_ids": customer_ids},
        )
        self.surge_factor = surge_factor
        self.customer_ids = customer_ids

    def apply(self, graph: nx.DiGraph) -> nx.DiGraph:
        g = fork_graph(graph)
        for n, attrs in g.nodes(data=True):
            if attrs.get("node_type") == "customer":
                if self.customer_ids is None or n in self.customer_ids:
                    if "demand_mean" in attrs:
                        attrs["demand_mean"] *= self.surge_factor
        return g
