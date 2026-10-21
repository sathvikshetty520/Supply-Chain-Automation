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


class CyberattackDisruption(Disruption):
    """Simulates a ransomware or IT/SCADA infrastructure attack paralyzing warehouse or factory automation.
    
    Severely throttles operational throughput, slashes fulfillment efficiency, and triples local processing times.
    """

    def __init__(self, target_node_id: str = "FAC_1", throughput_reduction: float = 0.85, duration_days: int = 21):
        super().__init__(
            name="Ransomware & Cyberattack",
            description=f"Cyberattack on {target_node_id} crippling automation throughput by {int(throughput_reduction*100)}%",
            parameters={
                "target_node_id": target_node_id,
                "throughput_reduction": throughput_reduction,
                "duration_days": duration_days,
            },
        )
        self.target_node_id = target_node_id
        self.throughput_reduction = throughput_reduction
        self.duration_days = duration_days

    def apply(self, graph: nx.DiGraph) -> nx.DiGraph:
        g = fork_graph(graph)
        if self.target_node_id in g.nodes:
            node_attrs = g.nodes[self.target_node_id]
            # Reduce node operational capacity
            orig_cap = float(node_attrs.get("daily_capacity", 100.0))
            node_attrs["daily_capacity"] = max(0.0, orig_cap * (1.0 - self.throughput_reduction))
            node_attrs["cyberattacked"] = True
            if self.throughput_reduction >= 1.0:
                node_attrs["operational"] = False

        # Inbound and outbound transit delays for affected node due to customs/paper clearance
        for u, v, attrs in g.edges(data=True):
            if u == self.target_node_id or v == self.target_node_id:
                attrs["lead_time_multiplier"] = attrs.get("lead_time_multiplier", 1.0) * 2.0
                attrs["disrupted"] = True
        return g


class CanalBlockageDisruption(Disruption):
    """Simulates a critical maritime canal blockage (e.g. Suez / Panama Canal drought / Red Sea diversion).
    
    Forces maritime rerouting around alternate capes, massively increasing transit lead times and fuel surcharges.
    """

    def __init__(self, lead_time_multiplier: float = 4.0, cost_multiplier: float = 1.60, affected_modes: Optional[List[str]] = None):
        affected_modes = affected_modes or ["ocean"]
        super().__init__(
            name="Canal Chokepoint & Blockage",
            description=f"Critical maritime canal blockage: {lead_time_multiplier}x transit delay, +{int((cost_multiplier-1.0)*100)}% fuel surcharge on {affected_modes} lanes",
            parameters={
                "lead_time_multiplier": lead_time_multiplier,
                "cost_multiplier": cost_multiplier,
                "affected_modes": affected_modes,
            },
        )
        self.lead_time_multiplier = lead_time_multiplier
        self.cost_multiplier = cost_multiplier
        self.affected_modes = affected_modes

    def apply(self, graph: nx.DiGraph) -> nx.DiGraph:
        g = fork_graph(graph)
        for u, v, attrs in g.edges(data=True):
            if attrs.get("mode") in self.affected_modes:
                attrs["lead_time_multiplier"] = attrs.get("lead_time_multiplier", 1.0) * self.lead_time_multiplier
                attrs["cost_multiplier"] = attrs.get("cost_multiplier", 1.0) * self.cost_multiplier
                attrs["co2_per_unit"] = attrs.get("co2_per_unit", 1.0) * 1.40  # Longer circumnavigation increases carbon emissions
                attrs["disrupted"] = True
        return g


class RawMaterialExportBanDisruption(Disruption):
    """Simulates geopolitical export bans, quota restrictions, or embargoes on critical upstream raw materials.
    
    Completely or severely cuts primary supplier output and spikes global spot procurement market prices.
    """

    def __init__(self, supplier_ids: Optional[List[str]] = None, capacity_curtailment: float = 0.90, tariff_surcharge: float = 1.75):
        supplier_ids = supplier_ids or ["SUP_1"]
        super().__init__(
            name="Raw Material Export Embargo",
            description=f"Geopolitical raw material export embargo on {supplier_ids}: {int(capacity_curtailment*100)}% capacity curtailment and {int((tariff_surcharge-1.0)*100)}% tariff spike",
            parameters={
                "supplier_ids": supplier_ids,
                "capacity_curtailment": capacity_curtailment,
                "tariff_surcharge": tariff_surcharge,
            },
        )
        self.supplier_ids = supplier_ids
        self.capacity_curtailment = capacity_curtailment
        self.tariff_surcharge = tariff_surcharge

    def apply(self, graph: nx.DiGraph) -> nx.DiGraph:
        g = fork_graph(graph)
        for sup_id in self.supplier_ids:
            if sup_id in g.nodes:
                attrs = g.nodes[sup_id]
                orig_cap = float(attrs.get("daily_capacity", 100.0))
                attrs["daily_capacity"] = max(0.0, orig_cap * (1.0 - self.capacity_curtailment))
                attrs["unit_cost"] = attrs.get("unit_cost", 20.0) * self.tariff_surcharge
                attrs["embargoed"] = True
                if self.capacity_curtailment >= 1.0:
                    attrs["operational"] = False

        # Inbound and outbound supplier edges incur tariff surge
        for u, v, attrs in g.edges(data=True):
            if u in self.supplier_ids:
                attrs["cost_multiplier"] = attrs.get("cost_multiplier", 1.0) * self.tariff_surcharge
                attrs["disrupted"] = True
        return g
