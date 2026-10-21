"""Pydantic request and response models for SC-Disrupt REST API."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class DisruptionRequest(BaseModel):
    disruption_type: Literal[
        "port_strike",
        "supplier_failure",
        "demand_surge",
        "currency_shock",
        "cyberattack",
        "canal_blockage",
        "raw_material_ban",
    ] = "port_strike"
    parameters: Dict[str, Any] = Field(default_factory=dict)


class SimulationRequest(BaseModel):
    disruption: Optional[DisruptionRequest] = None
    runs: int = Field(default=5, ge=1, le=50)
    sim_days: int = Field(default=45, ge=5, le=365)
    seed: int = Field(default=42)


class NetworkNodeResponse(BaseModel):
    id: str
    name: str
    type: str
    location: Optional[str] = None
    capacity: Optional[float] = None
    initial_inventory: Optional[float] = None
    safety_stock: Optional[float] = None


class NetworkLaneResponse(BaseModel):
    id: str
    origin: str
    destination: str
    mode: str
    lead_time_mean: float
    cost_per_unit: float
    capacity: float
    co2_per_unit: float


class NetworkGraphResponse(BaseModel):
    name: str
    nodes: List[NetworkNodeResponse]
    lanes: List[NetworkLaneResponse]
    total_nodes: int
    total_lanes: int


class MetricSummaryResponse(BaseModel):
    mean_service_level: float
    p10_service_level: float
    p90_service_level: float
    mean_cost: float
    p10_cost: float
    p90_cost: float
    mean_co2: float
    mean_revenue_at_risk: float
    node_stockout_probabilities: Dict[str, float] = Field(default_factory=dict)


class CascadeAnalysisResponse(BaseModel):
    disruption_name: str
    revenue_at_risk: float
    cost_delta: float
    service_level_delta: float
    first_stockout_node: Optional[str] = None
    first_stockout_day: Optional[int] = None
    baseline_summary: MetricSummaryResponse
    disrupted_summary: MetricSummaryResponse


class RecoveryActionResponse(BaseModel):
    agent: str
    action_type: str
    target_id: str
    description: str
    estimated_cost: float
    parameters: Dict[str, Any]


class ScoredPlanResponse(BaseModel):
    rank: int
    plan_id: str
    plan_name: str
    final_score: float
    sub_scores: Dict[str, float]
    post_recovery_service_level: float
    total_effective_cost: float
    co2_emissions_kg: float
    resilience_score: float
    is_pareto: bool
    actions: List[RecoveryActionResponse]


class RecoveryResponse(BaseModel):
    disruption_name: str
    cascade: CascadeAnalysisResponse
    plans: List[ScoredPlanResponse]
    executive_briefing: str
