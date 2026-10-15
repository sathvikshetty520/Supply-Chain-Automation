"""Shared domain types, enums, and dataclasses across scdisrupt modules."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(str, Enum):
    SUPPLIER = "supplier"
    FACTORY = "factory"
    WAREHOUSE = "warehouse"
    CUSTOMER = "customer"


class TransportMode(str, Enum):
    OCEAN = "ocean"
    AIR = "air"
    RAIL = "rail"
    ROAD = "road"


class ActionType(str, Enum):
    EXPEDITE_AIR = "expedite_air"
    SWITCH_SUPPLIER = "switch_supplier"
    PREPOSITION_STOCK = "preposition_stock"
    RAISE_SAFETY_STOCK = "raise_safety_stock"
    REROUTE_LANE = "reroute_lane"
    BUDGET_CAP = "budget_cap"


@dataclass
class Action:
    agent: str
    action_type: ActionType
    target_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    estimated_cost: float = 0.0
    description: str = ""


@dataclass
class Plan:
    id: str
    name: str
    description: str
    actions: List[Action] = field(default_factory=list)
    budget_limit: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeDailyMetrics:
    day: int
    node_id: str
    inventory_level: float
    backorders: float
    unmet_demand: float
    fulfilled_demand: float
    holding_cost: float
    stockout_penalty: float


@dataclass
class DailyMetrics:
    day: int
    total_inventory: float
    total_backorders: float
    total_stockout_events: int
    orders_placed: int
    orders_delivered: int
    orders_on_time: int
    daily_cost: float
    daily_co2: float
    revenue: float
    node_metrics: Dict[str, NodeDailyMetrics] = field(default_factory=dict)


@dataclass
class RunMetrics:
    seed: int
    total_cost: float
    total_revenue: float
    total_profit: float
    total_co2: float
    service_level: float  # on-time / total demand or orders fulfilled on time
    stockout_occurred: bool
    stockout_nodes: List[str]
    first_stockout_day: Optional[int]
    stockout_duration_days: Dict[str, int]
    daily_records: List[DailyMetrics] = field(default_factory=list)


@dataclass
class MonteCarloSummary:
    runs: int
    mean_cost: float
    p10_cost: float
    p90_cost: float
    mean_service_level: float
    p10_service_level: float
    p90_service_level: float
    mean_co2: float
    node_stockout_probabilities: Dict[str, float]
    mean_revenue_at_risk: float
    runs_details: List[RunMetrics] = field(default_factory=list)
