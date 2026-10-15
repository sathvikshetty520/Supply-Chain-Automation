"""Finance Agent: capital checks, budget ceilings, and FX limits."""
from typing import List
import networkx as nx

from scdisrupt.agents.base import BaseAgent
from scdisrupt.common.types import Action, ActionType
from scdisrupt.disruptions.cascade import CascadeAnalysis


class FinanceAgent(BaseAgent):
    """Enforces ROI hurdles, working capital limits, and budget caps."""

    def __init__(self, max_recovery_budget: float = 75000.0):
        super().__init__(name="Finance Agent", role="Budget governance and capital allocation")
        self.max_recovery_budget = max_recovery_budget

    def propose_actions(self, graph: nx.DiGraph, cascade: CascadeAnalysis) -> List[Action]:
        # Propose financial budget limits and checks
        return [
            Action(
                agent=self.name,
                action_type=ActionType.BUDGET_CAP,
                target_id="GLOBAL_BUDGET",
                parameters={"budget_cap": self.max_recovery_budget, "revenue_at_risk": cascade.revenue_at_risk},
                estimated_cost=0.0,
                description=f"Impose recovery cap at ${self.max_recovery_budget:,.0f} (protects against cost overruns)",
            )
        ]
