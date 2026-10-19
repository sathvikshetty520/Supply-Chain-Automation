"""FastAPI REST application for SC-Disrupt."""
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from scdisrupt.twin.loader import load_network_config, build_network_graph
from scdisrupt.twin.schema import NetworkConfig
from scdisrupt.disruptions.catalog import PortStrikeDisruption
from scdisrupt.disruptions.cascade import analyze_cascade
from scdisrupt.agents.orchestrator import AgentOrchestrator
from scdisrupt.scoring.counterfactual import evaluate_counterfactual_plans
from scdisrupt.scoring.scorer import PlanScorer
from scdisrupt.scoring.pareto import get_pareto_plans
from scdisrupt.explain.briefing import ExecutiveBriefingGenerator
from scdisrupt.api.factory import create_disruption
from scdisrupt.api.models import (
    SimulationRequest,
    NetworkGraphResponse,
    NetworkNodeResponse,
    NetworkLaneResponse,
    CascadeAnalysisResponse,
    MetricSummaryResponse,
    RecoveryResponse,
    ScoredPlanResponse,
    RecoveryActionResponse,
)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "configs" / "sample_network.yaml"

app = FastAPI(
    title="SC-Disrupt API",
    description="Autonomous Supply-Chain Disruption Simulator & Digital Twin REST API",
    version="0.1.0",
)

# Enable CORS for local dashboards / frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_current_graph():
    """Load default sample network graph."""
    if not DEFAULT_CONFIG_PATH.exists():
        raise HTTPException(status_code=500, detail="Default network config not found.")
    config = load_network_config(DEFAULT_CONFIG_PATH)
    return config, build_network_graph(config)


@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "scdisrupt", "version": "0.1.0"}


@app.get("/network", response_model=NetworkGraphResponse)
def get_network():
    """Retrieve digital twin topology, nodes, and transport lanes."""
    config, graph = get_current_graph()

    nodes: List[NetworkNodeResponse] = []
    for nid, attrs in graph.nodes(data=True):
        inv_pol = attrs.get("inventory_policy")
        nodes.append(
            NetworkNodeResponse(
                id=nid,
                name=attrs.get("name", nid),
                type=attrs.get("type", "unknown"),
                location=attrs.get("location"),
                capacity=attrs.get("daily_capacity") or (inv_pol.capacity if inv_pol else None),
                initial_inventory=inv_pol.initial_inventory if inv_pol else None,
                safety_stock=inv_pol.safety_stock if inv_pol else None,
            )
        )

    lanes: List[NetworkLaneResponse] = []
    for u, v, attrs in graph.edges(data=True):
        lanes.append(
            NetworkLaneResponse(
                id=attrs.get("id", f"{u}_{v}"),
                origin=u,
                destination=v,
                mode=attrs.get("mode", "ocean"),
                lead_time_mean=float(attrs.get("lead_time_mean", 1.0)),
                cost_per_unit=float(attrs.get("cost_per_unit", 1.0)),
                capacity=float(attrs.get("capacity", 100.0)),
                co2_per_unit=float(attrs.get("co2_per_unit", 1.0)),
            )
        )

    return NetworkGraphResponse(
        name=config.name,
        nodes=nodes,
        lanes=lanes,
        total_nodes=len(nodes),
        total_lanes=len(lanes),
    )


@app.post("/simulate/cascade", response_model=CascadeAnalysisResponse)
def simulate_cascade(req: SimulationRequest):
    """Simulate disruption cascade propagation and measure impact delta vs baseline."""
    _, graph = get_current_graph()

    if req.disruption:
        try:
            disruption = create_disruption(req.disruption.disruption_type, req.disruption.parameters)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
    else:
        disruption = PortStrikeDisruption(lead_time_multiplier=3.0)

    cascade = analyze_cascade(
        graph,
        disruption,
        runs=req.runs,
        sim_duration_days=req.sim_days,
        base_seed=req.seed,
    )

    return CascadeAnalysisResponse(
        disruption_name=cascade.disruption_name,
        revenue_at_risk=cascade.revenue_at_risk,
        cost_delta=cascade.cost_delta,
        service_level_delta=cascade.service_level_delta,
        first_stockout_node=cascade.first_stockout_node,
        first_stockout_day=cascade.first_stockout_day,
        baseline_summary=MetricSummaryResponse(
            mean_service_level=cascade.baseline_summary.mean_service_level,
            p10_service_level=cascade.baseline_summary.p10_service_level,
            p90_service_level=cascade.baseline_summary.p90_service_level,
            mean_cost=cascade.baseline_summary.mean_cost,
            p10_cost=cascade.baseline_summary.p10_cost,
            p90_cost=cascade.baseline_summary.p90_cost,
            mean_co2=cascade.baseline_summary.mean_co2,
            mean_revenue_at_risk=cascade.baseline_summary.mean_revenue_at_risk,
            node_stockout_probabilities=cascade.baseline_summary.node_stockout_probabilities,
        ),
        disrupted_summary=MetricSummaryResponse(
            mean_service_level=cascade.disrupted_summary.mean_service_level,
            p10_service_level=cascade.disrupted_summary.p10_service_level,
            p90_service_level=cascade.disrupted_summary.p90_service_level,
            mean_cost=cascade.disrupted_summary.mean_cost,
            p10_cost=cascade.disrupted_summary.p10_cost,
            p90_cost=cascade.disrupted_summary.p90_cost,
            mean_co2=cascade.disrupted_summary.mean_co2,
            mean_revenue_at_risk=cascade.disrupted_summary.mean_revenue_at_risk,
            node_stockout_probabilities=cascade.disrupted_summary.node_stockout_probabilities,
        ),
    )


@app.post("/recover", response_model=RecoveryResponse)
def trigger_recovery(req: SimulationRequest):
    """Orchestrate multi-agent recovery proposals, run counterfactual simulations, and generate briefing."""
    _, graph = get_current_graph()

    if req.disruption:
        try:
            disruption = create_disruption(req.disruption.disruption_type, req.disruption.parameters)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
    else:
        disruption = PortStrikeDisruption(lead_time_multiplier=3.0)

    # 1. Cascade analysis
    cascade = analyze_cascade(
        graph,
        disruption,
        runs=req.runs,
        sim_duration_days=req.sim_days,
        base_seed=req.seed,
    )

    # 2. Multi-agent plan synthesis
    orchestrator = AgentOrchestrator()
    plans = orchestrator.formulate_plans(graph, cascade)

    # 3. Counterfactual evaluations
    eval_results = evaluate_counterfactual_plans(
        graph,
        plans,
        runs=req.runs,
        sim_duration_days=req.sim_days,
        base_seed=req.seed,
    )

    scorer = PlanScorer()
    scored_plans = scorer.score_plans(eval_results)
    pareto_plans = get_pareto_plans(eval_results)
    pareto_ids = {p.plan.id for p in pareto_plans}

    # 4. Generate memo
    briefing_gen = ExecutiveBriefingGenerator()
    briefing = briefing_gen.generate_briefing(cascade, scored_plans, pareto_plans)

    # 5. Build response objects
    plan_responses: List[ScoredPlanResponse] = []
    for sp in scored_plans:
        r = sp.raw_result
        actions = [
            RecoveryActionResponse(
                agent=a.agent,
                action_type=a.action_type,
                target_id=a.target_id,
                description=a.description,
                estimated_cost=a.estimated_cost,
                parameters=a.parameters,
            )
            for a in r.plan.actions
        ]
        plan_responses.append(
            ScoredPlanResponse(
                rank=sp.rank,
                plan_id=sp.plan_id,
                plan_name=sp.plan_name,
                final_score=sp.final_score,
                sub_scores={
                    "cost": sp.normalized_cost_score,
                    "service": sp.normalized_service_score,
                    "co2": sp.normalized_co2_score,
                    "resilience": sp.normalized_resilience_score,
                },
                post_recovery_service_level=r.post_recovery_service_level,
                total_effective_cost=r.total_effective_cost,
                co2_emissions_kg=r.post_recovery_co2,
                resilience_score=r.resilience_score,
                is_pareto=sp.plan_id in pareto_ids,
                actions=actions,
            )
        )

    cascade_response = CascadeAnalysisResponse(
        disruption_name=cascade.disruption_name,
        revenue_at_risk=cascade.revenue_at_risk,
        cost_delta=cascade.cost_delta,
        service_level_delta=cascade.service_level_delta,
        first_stockout_node=cascade.first_stockout_node,
        first_stockout_day=cascade.first_stockout_day,
        baseline_summary=MetricSummaryResponse(
            mean_service_level=cascade.baseline_summary.mean_service_level,
            p10_service_level=cascade.baseline_summary.p10_service_level,
            p90_service_level=cascade.baseline_summary.p90_service_level,
            mean_cost=cascade.baseline_summary.mean_cost,
            p10_cost=cascade.baseline_summary.p10_cost,
            p90_cost=cascade.baseline_summary.p90_cost,
            mean_co2=cascade.baseline_summary.mean_co2,
            mean_revenue_at_risk=cascade.baseline_summary.mean_revenue_at_risk,
            node_stockout_probabilities=cascade.baseline_summary.node_stockout_probabilities,
        ),
        disrupted_summary=MetricSummaryResponse(
            mean_service_level=cascade.disrupted_summary.mean_service_level,
            p10_service_level=cascade.disrupted_summary.p10_service_level,
            p90_service_level=cascade.disrupted_summary.p90_service_level,
            mean_cost=cascade.disrupted_summary.mean_cost,
            p10_cost=cascade.disrupted_summary.p10_cost,
            p90_cost=cascade.disrupted_summary.p90_cost,
            mean_co2=cascade.disrupted_summary.mean_co2,
            mean_revenue_at_risk=cascade.disrupted_summary.mean_revenue_at_risk,
            node_stockout_probabilities=cascade.disrupted_summary.node_stockout_probabilities,
        ),
    )

    return RecoveryResponse(
        disruption_name=cascade.disruption_name,
        cascade=cascade_response,
        plans=plan_responses,
        executive_briefing=briefing,
    )
