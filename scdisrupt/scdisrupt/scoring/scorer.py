"""Multi-criteria utility scorer and plan ranker with configurable weights."""
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

from scdisrupt.scoring.counterfactual import PlanSimulationResult


@dataclass
class ScoredPlan:
    plan_id: str
    plan_name: str
    rank: int
    final_score: float  # 0.0 to 100.0
    normalized_cost_score: float
    normalized_service_score: float
    normalized_co2_score: float
    normalized_resilience_score: float
    raw_result: PlanSimulationResult


class PlanScorer:
    """Ranks plans using multi-criteria weighted utility scoring with min-max normalization."""

    def __init__(
        self,
        weight_cost: float = 0.35,
        weight_service_level: float = 0.35,
        weight_co2: float = 0.15,
        weight_resilience: float = 0.15,
    ):
        total_w = weight_cost + weight_service_level + weight_co2 + weight_resilience
        if total_w <= 0:
            raise ValueError("Total weight must be positive")
        self.w_cost = weight_cost / total_w
        self.w_service = weight_service_level / total_w
        self.w_co2 = weight_co2 / total_w
        self.w_resilience = weight_resilience / total_w

    def score_plans(self, results: List[PlanSimulationResult]) -> List[ScoredPlan]:
        """Compute weighted scores (0 to 100) and rank plans from best to worst."""
        if not results:
            return []

        costs = [r.total_effective_cost for r in results]
        services = [r.post_recovery_service_level for r in results]
        co2s = [r.post_recovery_co2 for r in results]
        resiliences = [r.resilience_score for r in results]

        def normalize_benefit(val: float, all_vals: List[float]) -> float:
            min_v, max_v = min(all_vals), max(all_vals)
            if max_v - min_v < 1e-9:
                return 1.0
            return (val - min_v) / (max_v - min_v)

        def normalize_cost(val: float, all_vals: List[float]) -> float:
            min_v, max_v = min(all_vals), max(all_vals)
            if max_v - min_v < 1e-9:
                return 1.0
            return (max_v - val) / (max_v - min_v)

        scored: List[ScoredPlan] = []
        for r in results:
            s_cost = normalize_cost(r.total_effective_cost, costs)
            s_service = normalize_benefit(r.post_recovery_service_level, services)
            s_co2 = normalize_cost(r.post_recovery_co2, co2s)
            s_resilience = normalize_benefit(r.resilience_score, resiliences)

            composite = (
                self.w_cost * s_cost
                + self.w_service * s_service
                + self.w_co2 * s_co2
                + self.w_resilience * s_resilience
            ) * 100.0

            scored.append(
                ScoredPlan(
                    plan_id=r.plan.id,
                    plan_name=r.plan.name,
                    rank=0,
                    final_score=float(np.round(composite, 2)),
                    normalized_cost_score=float(np.round(s_cost * 100, 1)),
                    normalized_service_score=float(np.round(s_service * 100, 1)),
                    normalized_co2_score=float(np.round(s_co2 * 100, 1)),
                    normalized_resilience_score=float(np.round(s_resilience * 100, 1)),
                    raw_result=r,
                )
            )

        # Rank descending by final score
        scored.sort(key=lambda x: x.final_score, reverse=True)
        for i, p in enumerate(scored):
            p.rank = i + 1

        return scored
