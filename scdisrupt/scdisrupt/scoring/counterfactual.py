"""Counterfactual engine: applies candidate plans to twin and simulates outcomes."""
from dataclasses import dataclass
from typing import Dict, List
import networkx as nx

from scdisrupt.common.types import ActionType, MonteCarloSummary, Plan
from scdisrupt.simulation.montecarlo import run_monte_carlo
from scdisrupt.twin.state import fork_graph


@dataclass
class PlanSimulationResult:
    plan: Plan
    summary: MonteCarloSummary
    action_cost: float
    total_effective_cost: float
    post_recovery_service_level: float
    post_recovery_co2: float
    resilience_score: float  # 1.0 - mean stockout probability


def apply_plan_to_graph(disrupted_graph: nx.DiGraph, plan: Plan) -> nx.DiGraph:
    """Mutate a copy of the disrupted graph by enacting all actions within the plan."""
    g = fork_graph(disrupted_graph)

    for act in plan.actions:
        if act.action_type == ActionType.SWITCH_SUPPLIER:
            target_s = act.target_id
            if target_s in g.nodes:
                g.nodes[target_s]["daily_capacity"] += act.parameters.get("capacity_boost", 50.0)
                g.nodes[target_s]["operational"] = True

        elif act.action_type == ActionType.EXPEDITE_AIR:
            # Slashes outbound lead time from supplier
            sup_id = act.target_id
            for u, v, attrs in g.out_edges(sup_id, data=True):
                attrs["lead_time_mean"] = max(1.0, attrs.get("lead_time_mean", 4.0) * act.parameters.get("speed_up_factor", 0.35))
                attrs["cost_multiplier"] = attrs.get("cost_multiplier", 1.0) * act.parameters.get("cost_penalty", 3.0)

        elif act.action_type == ActionType.REROUTE_LANE:
            lane_id = act.target_id
            for u, v, attrs in g.edges(data=True):
                if attrs.get("lane_id") == lane_id:
                    attrs["mode"] = act.parameters.get("new_mode", "air")
                    attrs["lead_time_mean"] = max(1.0, attrs.get("lead_time_mean", 10.0) * act.parameters.get("lead_time_reduction", 0.30))
                    attrs["cost_multiplier"] = attrs.get("cost_multiplier", 1.0) * act.parameters.get("cost_multiplier", 2.8)
                    attrs["co2_multiplier"] = attrs.get("co2_multiplier", 1.0) * act.parameters.get("co2_multiplier", 3.5)

        elif act.action_type == ActionType.RAISE_SAFETY_STOCK:
            wh_id = act.target_id
            if wh_id in g.nodes:
                g.nodes[wh_id]["safety_stock"] = act.parameters.get("new_safety_stock", g.nodes[wh_id]["safety_stock"] * 1.5)
                g.nodes[wh_id]["reorder_point"] = max(g.nodes[wh_id]["reorder_point"], g.nodes[wh_id]["safety_stock"] * 1.8)

        elif act.action_type == ActionType.PREPOSITION_STOCK:
            wh_id = act.target_id
            if wh_id in g.nodes:
                boost = act.parameters.get("preposition_quantity", 100.0)
                cap = g.nodes[wh_id].get("capacity", 500.0)
                g.nodes[wh_id]["initial_inventory"] = min(cap, g.nodes[wh_id].get("initial_inventory", 0.0) + boost)

    return g


def evaluate_counterfactual_plans(
    disrupted_graph: nx.DiGraph,
    plans: List[Plan],
    runs: int = 25,
    sim_duration_days: int = 60,
    base_seed: int = 42,
) -> List[PlanSimulationResult]:
    """Simulate each plan counterfactually across Monte Carlo runs and return standardized results."""
    results: List[PlanSimulationResult] = []

    for plan in plans:
        # Fork and apply plan actions
        plan_graph = apply_plan_to_graph(disrupted_graph, plan)

        # Run Monte Carlo simulation for this plan
        summary = run_monte_carlo(plan_graph, runs=runs, base_seed=base_seed, sim_duration_days=sim_duration_days)

        # Compute capex/implementation action cost
        plan_action_cost = sum(act.estimated_cost for act in plan.actions)
        total_effective_cost = float(round(summary.mean_cost + plan_action_cost, 2))

        # Compute network-wide resilience score: 1.0 - average stockout probability
        probs = list(summary.node_stockout_probabilities.values())
        avg_stockout_prob = float(sum(probs) / len(probs)) if probs else 0.0
        resilience_score = float(round(max(0.0, 1.0 - avg_stockout_prob), 4))

        results.append(
            PlanSimulationResult(
                plan=plan,
                summary=summary,
                action_cost=plan_action_cost,
                total_effective_cost=total_effective_cost,
                post_recovery_service_level=summary.mean_service_level,
                post_recovery_co2=summary.mean_co2,
                resilience_score=resilience_score,
            )
        )

    return results
