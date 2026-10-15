"""Orchestrator combining multi-agent proposals into 3 distinct, actionable recovery plans."""
from typing import List
import networkx as nx

from scdisrupt.agents.procurement import ProcurementAgent
from scdisrupt.agents.inventory import InventoryAgent
from scdisrupt.agents.routing import RoutingAgent
from scdisrupt.agents.finance import FinanceAgent
from scdisrupt.common.types import ActionType, Plan
from scdisrupt.disruptions.cascade import CascadeAnalysis


class AgentOrchestrator:
    """Coordinates specialized agents and synthesizes 3 candidate recovery strategies."""

    def __init__(self):
        self.procurement_agent = ProcurementAgent()
        self.inventory_agent = InventoryAgent()
        self.routing_agent = RoutingAgent()
        self.finance_agent = FinanceAgent()

    def formulate_plans(self, graph: nx.DiGraph, cascade: CascadeAnalysis) -> List[Plan]:
        """Synthesize agent action proposals into 3 distinct plans (A, B, C)."""
        proc_actions = self.procurement_agent.propose_actions(graph, cascade)
        inv_actions = self.inventory_agent.propose_actions(graph, cascade)
        rout_actions = self.routing_agent.propose_actions(graph, cascade)
        fin_actions = self.finance_agent.propose_actions(graph, cascade)

        # Plan A: Expedite Air Freight (speed priority, slashes delivery times)
        air_actions = [a for a in rout_actions if a.action_type == ActionType.REROUTE_LANE]
        expedite_actions = [a for a in proc_actions if a.action_type == ActionType.EXPEDITE_AIR]
        plan_a_actions = air_actions[:1] + expedite_actions[:1] + fin_actions
        plan_a = Plan(
            id="PLAN_A",
            name="Plan A: Expedite Air Freight",
            description="Rapid modal shift chartering air cargo to bypass maritime bottlenecks and expedite shipments.",
            actions=plan_a_actions,
            budget_limit=70000.0,
            metadata={"strategy_focus": "Speed & Service Level", "lead_time_reduction": "High"},
        )

        # Plan B: Dual Sourcing & Supplier Pivot (procurement resilience)
        switch_actions = [a for a in proc_actions if a.action_type == ActionType.SWITCH_SUPPLIER]
        ss_actions = [a for a in inv_actions if a.action_type == ActionType.RAISE_SAFETY_STOCK]
        plan_b_actions = switch_actions[:1] + ss_actions[:1] + fin_actions
        plan_b = Plan(
            id="PLAN_B",
            name="Plan B: Dual Sourcing Pivot",
            description="Re-route procurement orders to secondary regional suppliers and moderately increase buffer inventory.",
            actions=plan_b_actions,
            budget_limit=55000.0,
            metadata={"strategy_focus": "Sourcing Redundancy", "procurement_pivot": "Primary"},
        )

        # Plan C: Regional Pre-Positioning & Buffer Surge (inventory protection)
        prep_actions = [a for a in inv_actions if a.action_type == ActionType.PREPOSITION_STOCK]
        all_ss = [a for a in inv_actions if a.action_type == ActionType.RAISE_SAFETY_STOCK]
        plan_c_actions = prep_actions[:1] + all_ss + fin_actions
        plan_c = Plan(
            id="PLAN_C",
            name="Plan C: Regional Pre-Positioning",
            description="Pre-position safety stock directly into vulnerable downstream warehouses before stockouts propagate.",
            actions=plan_c_actions,
            budget_limit=45000.0,
            metadata={"strategy_focus": "Downstream Buffering", "capex_efficiency": "High"},
        )

        return [plan_a, plan_b, plan_c]
