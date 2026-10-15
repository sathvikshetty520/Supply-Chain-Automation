"""Loader to convert YAML/JSON network definition into typed NetworkX DiGraph."""
from pathlib import Path
from typing import Union
import yaml
import networkx as nx

from scdisrupt.common.types import NodeType
from scdisrupt.twin.schema import NetworkConfig


def load_network_config(source: Union[str, Path, dict]) -> NetworkConfig:
    """Load and validate a NetworkConfig from a file path or dictionary."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Network config file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    elif isinstance(source, dict):
        data = source
    else:
        raise ValueError(f"Unsupported source type: {type(source)}")

    return NetworkConfig.model_validate(data)


def build_network_graph(config: NetworkConfig) -> nx.DiGraph:
    """Construct a NetworkX DiGraph with typed nodes and edges from validated NetworkConfig."""
    G = nx.DiGraph(name=config.name, version=config.version, description=config.description)

    # 1. Add Suppliers
    for s in config.suppliers:
        G.add_node(
            s.id,
            node_type=NodeType.SUPPLIER,
            name=s.name,
            location=s.location,
            daily_capacity=s.daily_capacity,
            unit_cost=s.unit_cost,
            reliability=s.reliability,
            current_capacity=s.daily_capacity,
            operational=True,
        )

    # 2. Add Factories
    for f in config.factories:
        pol = f.inventory_policy
        G.add_node(
            f.id,
            node_type=NodeType.FACTORY,
            name=f.name,
            location=f.location,
            daily_capacity=f.daily_capacity,
            holding_cost_per_day=f.holding_cost_per_day,
            initial_inventory=pol.initial_inventory,
            reorder_point=pol.reorder_point,
            order_quantity=pol.order_quantity,
            safety_stock=pol.safety_stock,
            capacity=pol.capacity,
            current_inventory=pol.initial_inventory,
            current_capacity=f.daily_capacity,
            operational=True,
        )

    # 3. Add Warehouses
    for w in config.warehouses:
        pol = w.inventory_policy
        G.add_node(
            w.id,
            node_type=NodeType.WAREHOUSE,
            name=w.name,
            location=w.location,
            holding_cost_per_day=w.holding_cost_per_day,
            stockout_penalty_per_day=w.stockout_penalty_per_day,
            initial_inventory=pol.initial_inventory,
            reorder_point=pol.reorder_point,
            order_quantity=pol.order_quantity,
            safety_stock=pol.safety_stock,
            capacity=pol.capacity,
            current_inventory=pol.initial_inventory,
            operational=True,
        )

    # 4. Add Customers
    for c in config.customers:
        G.add_node(
            c.id,
            node_type=NodeType.CUSTOMER,
            name=c.name,
            location=c.location,
            revenue_per_unit=c.revenue_per_unit,
            demand_distribution=c.demand.distribution,
            demand_mean=c.demand.mean,
            demand_std=c.demand.std,
            operational=True,
        )

    # 5. Add Lanes (Edges)
    for lane in config.lanes:
        G.add_edge(
            lane.origin,
            lane.destination,
            lane_id=lane.id,
            mode=lane.mode,
            lead_time_mean=lane.lead_time_mean,
            lead_time_std=lane.lead_time_std,
            cost_per_unit=lane.cost_per_unit,
            capacity=lane.capacity,
            co2_per_unit=lane.co2_per_unit,
            disrupted=False,
            lead_time_multiplier=1.0,
            cost_multiplier=1.0,
        )

    return G
