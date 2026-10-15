"""SimPy discrete-event simulation model of end-to-end multi-echelon supply chain."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import networkx as nx
import numpy as np
import simpy

from scdisrupt.common.types import NodeType, NodeDailyMetrics, RunMetrics
from scdisrupt.common.seeds import get_rng
from scdisrupt.simulation.distributions import sample_lead_time, sample_demand
from scdisrupt.simulation.metrics import SimulationMetricsCollector


@dataclass
class Shipment:
    shipment_id: str
    origin: str
    destination: str
    quantity: float
    departure_time: float
    expected_arrival_time: float
    cost: float
    co2: float


class SupplyChainNode:
    """Represents a stateful node (Supplier, Factory, Warehouse, Customer) in the SimPy environment."""

    def __init__(self, node_id: str, attrs: dict):
        self.node_id = node_id
        self.attrs = attrs
        self.node_type: NodeType = attrs.get("node_type")
        self.inventory: float = float(attrs.get("initial_inventory", 0.0))
        self.pipeline_inventory: float = 0.0  # orders placed but in transit
        self.backorders: float = 0.0
        self.capacity: float = float(attrs.get("capacity", 1e9))
        self.reorder_point: float = float(attrs.get("reorder_point", 0.0))
        self.order_quantity: float = float(attrs.get("order_quantity", 0.0))
        self.safety_stock: float = float(attrs.get("safety_stock", 0.0))
        self.holding_cost_rate: float = float(attrs.get("holding_cost_per_day", 0.0))
        self.penalty_cost_rate: float = float(attrs.get("stockout_penalty_per_day", 20.0))
        self.daily_capacity: float = float(attrs.get("daily_capacity", 1e9))
        self.operational: bool = attrs.get("operational", True)

        # Tracking for the current day
        self.today_unmet_demand: float = 0.0
        self.today_fulfilled_demand: float = 0.0
        self.today_revenue: float = 0.0

    def reset_daily_counters(self):
        self.today_unmet_demand = 0.0
        self.today_fulfilled_demand = 0.0
        self.today_revenue = 0.0


class SupplyChainSimulation:
    """Discrete-event simulation engine coordinating SimPy processes across network nodes."""

    def __init__(self, graph: nx.DiGraph, seed: int = 42, sim_duration_days: int = 60):
        self.graph = graph
        self.seed = seed
        self.rng = get_rng(seed)
        self.sim_duration_days = sim_duration_days

        self.env = simpy.Environment()
        self.collector = SimulationMetricsCollector(seed=seed)

        # Initialize node objects
        self.nodes: Dict[str, SupplyChainNode] = {}
        for nid, attrs in self.graph.nodes(data=True):
            self.nodes[nid] = SupplyChainNode(nid, attrs)

        # Daily in-flight accounting
        self.daily_transport_cost = 0.0
        self.daily_transport_co2 = 0.0
        self.daily_orders_placed = 0
        self.daily_orders_delivered = 0
        self.daily_orders_on_time = 0
        self._shipment_counter = 0

    def run(self) -> RunMetrics:
        """Execute the SimPy simulation until sim_duration_days."""
        self.env.process(self._daily_clock_process())
        self.env.run(until=self.sim_duration_days + 0.001)
        return self.collector.compute_run_summary()

    def _daily_clock_process(self):
        """Ticks once per day to trigger customer demand, inventory checks, and daily metrics."""
        for current_day in range(self.sim_duration_days):
            # Reset daily counters
            self.daily_transport_cost = 0.0
            self.daily_transport_co2 = 0.0
            self.daily_orders_placed = 0
            self.daily_orders_delivered = 0
            self.daily_orders_on_time = 0
            for node in self.nodes.values():
                node.reset_daily_counters()

            # 1. Process customer demand & orders
            self._process_customer_demand(current_day)

            # 2. Check replenishments (Warehouses & Factory inventory review)
            self._review_replenishment_policies(current_day)

            # Collect end-of-day metrics for current_day
            node_records = {}
            total_revenue_today = 0.0
            for nid, node in self.nodes.items():
                total_revenue_today += node.today_revenue
                holding = max(0.0, node.inventory) * node.holding_cost_rate
                penalty = (node.today_unmet_demand + node.backorders) * node.penalty_cost_rate
                node_records[nid] = NodeDailyMetrics(
                    day=current_day,
                    node_id=nid,
                    inventory_level=float(node.inventory),
                    backorders=float(node.backorders),
                    unmet_demand=float(node.today_unmet_demand),
                    fulfilled_demand=float(node.today_fulfilled_demand),
                    holding_cost=float(holding),
                    stockout_penalty=float(penalty),
                )

            self.collector.record_day(
                day=current_day,
                node_records=node_records,
                daily_transport_cost=self.daily_transport_cost,
                daily_co2=self.daily_transport_co2,
                daily_revenue=total_revenue_today,
                orders_placed=self.daily_orders_placed,
                orders_delivered=self.daily_orders_delivered,
                orders_on_time=self.daily_orders_on_time,
            )

            # Advance clock by 1.0 day
            yield self.env.timeout(1.0)


    def _process_customer_demand(self, current_day: int):
        """Generate stochastic demand for each customer and fulfill from upstream warehouses."""
        for cust_id, cust_node in self.nodes.items():
            if cust_node.node_type != NodeType.CUSTOMER:
                continue

            dist = cust_node.attrs.get("demand_distribution", "normal")
            mean = cust_node.attrs.get("demand_mean", 20.0)
            std = cust_node.attrs.get("demand_std", 5.0)
            demand_qty = sample_demand(dist, mean, std, self.rng)
            unit_revenue = cust_node.attrs.get("revenue_per_unit", 120.0)

            # Upstream warehouse(s) feeding this customer
            in_edges = list(self.graph.in_edges(cust_id, data=True))
            if not in_edges:
                continue

            # Route to primary upstream warehouse
            u, _, lane_attrs = in_edges[0]
            wh_node = self.nodes[u]

            # Fulfill immediately from warehouse inventory
            available = max(0.0, wh_node.inventory)
            to_fulfill = min(available, demand_qty)
            unmet = demand_qty - to_fulfill

            wh_node.inventory -= to_fulfill
            wh_node.backorders += unmet

            cust_node.today_fulfilled_demand += to_fulfill
            cust_node.today_unmet_demand += unmet
            cust_node.today_revenue += to_fulfill * unit_revenue

            # Lane cost and CO2 for local last-mile transit
            c_unit = lane_attrs.get("cost_per_unit", 2.0) * lane_attrs.get("cost_multiplier", 1.0)
            co2_unit = lane_attrs.get("co2_per_unit", 0.5)
            self.daily_transport_cost += to_fulfill * c_unit
            self.daily_transport_co2 += to_fulfill * co2_unit

    def _review_replenishment_policies(self, current_day: int):
        """Continuous/periodic review (s, Q): if inventory + pipeline <= reorder_point, place order."""
        # A. Warehouses requesting from Factory
        for nid, node in self.nodes.items():
            if node.node_type == NodeType.WAREHOUSE:
                effective_inventory = node.inventory + node.pipeline_inventory
                if effective_inventory <= node.reorder_point:
                    order_qty = node.order_quantity
                    in_edges = list(self.graph.in_edges(nid, data=True))
                    if in_edges:
                        origin_id, _, lane_attrs = in_edges[0]
                        self._trigger_shipment(origin_id, nid, order_qty, lane_attrs)

        # B. Factories requesting from Suppliers
        for nid, node in self.nodes.items():
            if node.node_type == NodeType.FACTORY:
                effective_inventory = node.inventory + node.pipeline_inventory
                if effective_inventory <= node.reorder_point:
                    order_qty = node.order_quantity
                    in_edges = list(self.graph.in_edges(nid, data=True))
                    # Pick an operational supplier with available capacity
                    chosen_edge = None
                    for u, _, lane in in_edges:
                        sup = self.nodes[u]
                        if sup.operational and sup.daily_capacity > 0:
                            chosen_edge = (u, lane)
                            break
                    if chosen_edge:
                        origin_id, lane_attrs = chosen_edge
                        self._trigger_shipment(origin_id, nid, order_qty, lane_attrs)

    def _trigger_shipment(self, origin_id: str, dest_id: str, quantity: float, lane_attrs: dict):
        """Spawn a SimPy transit process representing lead time, transit costs, and arrival."""
        origin_node = self.nodes[origin_id]
        dest_node = self.nodes[dest_id]

        # Check origin capacity / operation
        if not origin_node.operational or origin_node.daily_capacity <= 0:
            return  # supplier offline / factory halted

        # If origin is a factory, check factory component inventory
        if origin_node.node_type == NodeType.FACTORY:
            if origin_node.inventory < quantity:
                # partial fulfillment or backorder at factory
                actual_qty = max(0.0, origin_node.inventory)
                origin_node.inventory -= actual_qty
                quantity = actual_qty
                if quantity <= 0:
                    return
            else:
                origin_node.inventory -= quantity

        # Update destination pipeline inventory
        dest_node.pipeline_inventory += quantity
        self.daily_orders_placed += 1
        self._shipment_counter += 1

        # Calculate lead time with lognormal stochasticity and lane multipliers
        lt_mean = lane_attrs.get("lead_time_mean", 5.0) * lane_attrs.get("lead_time_multiplier", 1.0)
        lt_std = lane_attrs.get("lead_time_std", 1.0)
        lead_time = sample_lead_time(lt_mean, lt_std, self.rng)

        # Calculate transit cost and carbon
        cost_unit = lane_attrs.get("cost_per_unit", 5.0) * lane_attrs.get("cost_multiplier", 1.0)
        co2_unit = lane_attrs.get("co2_per_unit", 1.0)
        total_shipment_cost = quantity * cost_unit
        total_shipment_co2 = quantity * co2_unit

        self.daily_transport_cost += total_shipment_cost
        self.daily_transport_co2 += total_shipment_co2

        shipment = Shipment(
            shipment_id=f"SHP_{self._shipment_counter:04d}",
            origin=origin_id,
            destination=dest_id,
            quantity=quantity,
            departure_time=self.env.now,
            expected_arrival_time=self.env.now + lt_mean,
            cost=total_shipment_cost,
            co2=total_shipment_co2,
        )

        self.env.process(self._transit_process(shipment, lead_time))

    def _transit_process(self, shipment: Shipment, lead_time: float):
        """SimPy process that pauses for lead_time and deposits units into destination inventory."""
        yield self.env.timeout(lead_time)

        dest_node = self.nodes[shipment.destination]
        dest_node.pipeline_inventory = max(0.0, dest_node.pipeline_inventory - shipment.quantity)
        
        # Resolve backorders first
        if dest_node.backorders > 0:
            cleared_backorders = min(dest_node.backorders, shipment.quantity)
            dest_node.backorders -= cleared_backorders
            remaining_qty = shipment.quantity - cleared_backorders
        else:
            remaining_qty = shipment.quantity

        dest_node.inventory = min(dest_node.capacity, dest_node.inventory + remaining_qty)
        self.daily_orders_delivered += 1
        if self.env.now <= shipment.expected_arrival_time + 0.5:
            self.daily_orders_on_time += 1
