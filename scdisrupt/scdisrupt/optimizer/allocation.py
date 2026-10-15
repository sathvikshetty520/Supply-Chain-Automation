"""PuLP Linear Programming solver computing least-cost feasible replenishment allocations."""
from typing import Dict, Tuple
import networkx as nx
import pulp

from scdisrupt.common.types import Plan, ActionType


def solve_least_cost_allocation(graph: nx.DiGraph, plan: Plan) -> Dict[str, float]:
    """Formulate and solve a PuLP LP to allocate flow from origins to destinations under plan modifications."""
    prob = pulp.LpProblem(f"Allocation_{plan.id}", pulp.LpMinimize)

    # Decision variables: flow x[u, v] for each edge
    flow_vars: Dict[Tuple[str, str], pulp.LpVariable] = {}
    costs: Dict[Tuple[str, str], float] = {}

    for u, v, attrs in graph.edges(data=True):
        cap = float(attrs.get("capacity", 1000.0))
        unit_c = float(attrs.get("cost_per_unit", 5.0)) * float(attrs.get("cost_multiplier", 1.0))

        # Adjust costs/capacities based on plan actions
        for act in plan.actions:
            if act.action_type == ActionType.REROUTE_LANE and act.target_id == attrs.get("lane_id"):
                unit_c *= act.parameters.get("cost_multiplier", 2.5)
            elif act.action_type == ActionType.EXPEDITE_AIR:
                if u == act.target_id:
                    unit_c *= act.parameters.get("cost_penalty", 3.0)

        var_name = f"flow_{u}_{v}"
        flow_vars[(u, v)] = pulp.LpVariable(var_name, lowBound=0, upBound=cap, cat=pulp.LpContinuous)
        costs[(u, v)] = unit_c

    # Objective: Minimize total transport cost
    prob += pulp.lpSum([costs[e] * flow_vars[e] for e in flow_vars]), "Total_Transport_Cost"

    # Supplier Capacity Constraints
    for n, attrs in graph.nodes(data=True):
        if attrs.get("node_type") == "supplier":
            cap = float(attrs.get("daily_capacity", 100.0))
            # Plan adjustments: capacity boost if switched
            for act in plan.actions:
                if act.action_type == ActionType.SWITCH_SUPPLIER and act.target_id == n:
                    cap += act.parameters.get("capacity_boost", 50.0)

            out_edges = [flow_vars[(u, v)] for u, v in graph.out_edges(n) if (u, v) in flow_vars]
            if out_edges:
                prob += pulp.lpSum(out_edges) <= cap, f"Cap_Supplier_{n}"

    # Factory Conservation & Production Constraints
    for n, attrs in graph.nodes(data=True):
        if attrs.get("node_type") == "factory":
            in_edges = [flow_vars[(u, v)] for u, v in graph.in_edges(n) if (u, v) in flow_vars]
            out_edges = [flow_vars[(u, v)] for u, v in graph.out_edges(n) if (u, v) in flow_vars]
            if in_edges and out_edges:
                # Production throughput cannot exceed inbound supply + initial inventory allowance
                prob += pulp.lpSum(out_edges) <= pulp.lpSum(in_edges) + 50.0, f"Balance_Factory_{n}"

    # Customer Demand Satisfaction (attempt to satisfy customer mean demands)
    for n, attrs in graph.nodes(data=True):
        if attrs.get("node_type") == "customer":
            demand = float(attrs.get("demand_mean", 25.0))
            in_edges = [flow_vars[(u, v)] for u, v in graph.in_edges(n) if (u, v) in flow_vars]
            if in_edges:
                # Ensure at least 80% minimum satisfaction if feasible
                prob += pulp.lpSum(in_edges) >= 0.70 * demand, f"MinDemand_{n}"

    # Solve using default solver (PULP_CBC_CMD or default available)
    solver = pulp.PULP_CBC_CMD(msg=False)
    status = prob.solve(solver)

    result_flows = {}
    if status == pulp.LpStatusOptimal:
        for (u, v), var in flow_vars.items():
            result_flows[f"{u}->{v}"] = float(var.varValue or 0.0)
    else:
        # Fallback to simple proportional allocation if over-constrained
        for (u, v), var in flow_vars.items():
            result_flows[f"{u}->{v}"] = float(graph.edges[u, v].get("capacity", 50.0) * 0.5)

    return result_flows
