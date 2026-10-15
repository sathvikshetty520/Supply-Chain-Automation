"""Cascading failure analysis comparing baseline vs disrupted digital twin performance."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import networkx as nx
import numpy as np

from scdisrupt.common.types import MonteCarloSummary, RunMetrics
from scdisrupt.disruptions.base import Disruption
from scdisrupt.simulation.montecarlo import run_monte_carlo


@dataclass
class StockoutEvent:
    day: int
    node_id: str
    node_name: str
    unmet_demand: float
    backorders: float


@dataclass
class CascadeAnalysis:
    disruption_name: str
    baseline_summary: MonteCarloSummary
    disrupted_summary: MonteCarloSummary
    cost_delta: float
    service_level_delta: float
    revenue_at_risk: float
    first_stockout_node: Optional[str]
    first_stockout_day: Optional[int]
    stockout_timeline: List[StockoutEvent] = field(default_factory=list)
    vulnerable_nodes_ranked: List[Dict[str, float]] = field(default_factory=list)


def analyze_cascade(
    baseline_graph: nx.DiGraph,
    disruption: Disruption,
    runs: int = 25,
    sim_duration_days: int = 60,
    base_seed: int = 42,
) -> CascadeAnalysis:
    """Simulate baseline vs disrupted network, tracing the propagation cascade of stockouts."""
    # 1. Baseline Monte Carlo
    base_mc = run_monte_carlo(baseline_graph, runs=runs, base_seed=base_seed, sim_duration_days=sim_duration_days)

    # 2. Apply Disruption & run Disrupted Monte Carlo
    disrupted_graph = disruption.apply(baseline_graph)
    disrupt_mc = run_monte_carlo(disrupted_graph, runs=runs, base_seed=base_seed, sim_duration_days=sim_duration_days)

    # 3. Analyze propagation cascade using deterministic representative run (first run)
    rep_run: RunMetrics = disrupt_mc.runs_details[0] if disrupt_mc.runs_details else None

    stockout_timeline: List[StockoutEvent] = []
    seen_nodes = set()
    first_node = None
    first_day = None

    if rep_run:
        for daily in rep_run.daily_records:
            for nid, nmetric in daily.node_metrics.items():
                if nmetric.unmet_demand > 0 or (nmetric.inventory_level <= 0 and nmetric.backorders > 0):
                    if nid not in seen_nodes:
                        seen_nodes.add(nid)
                        node_name = disrupted_graph.nodes[nid].get("name", nid)
                        stockout_timeline.append(
                            StockoutEvent(
                                day=daily.day,
                                node_id=nid,
                                node_name=node_name,
                                unmet_demand=float(np.round(nmetric.unmet_demand, 2)),
                                backorders=float(np.round(nmetric.backorders, 2)),
                            )
                        )
                        if first_node is None:
                            first_node = nid
                            first_day = daily.day

    # Sort stockout timeline by day
    stockout_timeline.sort(key=lambda x: x.day)

    # Rank nodes by disrupted stockout probability delta
    vulnerable_nodes = []
    for nid, d_prob in disrupt_mc.node_stockout_probabilities.items():
        b_prob = base_mc.node_stockout_probabilities.get(nid, 0.0)
        vulnerable_nodes.append({
            "node_id": nid,
            "node_name": baseline_graph.nodes[nid].get("name", nid),
            "disrupted_prob": d_prob,
            "baseline_prob": b_prob,
            "delta_prob": float(np.round(d_prob - b_prob, 4)),
        })
    vulnerable_nodes.sort(key=lambda x: x["disrupted_prob"], reverse=True)

    cost_delta = float(np.round(disrupt_mc.mean_cost - base_mc.mean_cost, 2))
    sl_delta = float(np.round(disrupt_mc.mean_service_level - base_mc.mean_service_level, 4))
    
    # Quantified revenue at risk
    base_rev = np.mean([r.total_revenue for r in base_mc.runs_details]) if base_mc.runs_details else 0.0
    disr_rev = np.mean([r.total_revenue for r in disrupt_mc.runs_details]) if disrupt_mc.runs_details else 0.0
    revenue_at_risk = float(np.round(max(0.0, base_rev - disr_rev), 2))

    return CascadeAnalysis(
        disruption_name=disruption.name,
        baseline_summary=base_mc,
        disrupted_summary=disrupt_mc,
        cost_delta=cost_delta,
        service_level_delta=sl_delta,
        revenue_at_risk=revenue_at_risk,
        first_stockout_node=first_node,
        first_stockout_day=first_day,
        stockout_timeline=stockout_timeline,
        vulnerable_nodes_ranked=vulnerable_nodes,
    )
