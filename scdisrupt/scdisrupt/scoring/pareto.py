"""Pareto non-dominated set calculation across Cost, Service Level, and CO2."""
from typing import List
from scdisrupt.scoring.counterfactual import PlanSimulationResult


def is_pareto_efficient(costs: List[float], service_levels: List[float], co2s: List[float]) -> List[bool]:
    """Identify Pareto efficient points (Min Cost, Max Service Level, Min CO2)."""
    n = len(costs)
    is_efficient = [True] * n

    for i in range(n):
        for j in range(n):
            if i != j:
                # Point j dominates point i if j is at least as good in all criteria and strictly better in at least one
                j_not_worse = (
                    costs[j] <= costs[i]
                    and service_levels[j] >= service_levels[i]
                    and co2s[j] <= co2s[i]
                )
                j_strictly_better = (
                    costs[j] < costs[i]
                    or service_levels[j] > service_levels[i]
                    or co2s[j] < co2s[i]
                )
                if j_not_worse and j_strictly_better:
                    is_efficient[i] = False
                    break
    return is_efficient


def get_pareto_plans(results: List[PlanSimulationResult]) -> List[PlanSimulationResult]:
    """Filter plan simulation results to only the Pareto non-dominated set."""
    if not results:
        return []

    costs = [r.total_effective_cost for r in results]
    sls = [r.post_recovery_service_level for r in results]
    co2s = [r.post_recovery_co2 for r in results]

    mask = is_pareto_efficient(costs, sls, co2s)
    return [res for res, flag in zip(results, mask) if flag]
