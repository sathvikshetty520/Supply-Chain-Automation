"""Procurement Agent: identifies alternate supplier sources and expediting opportunities."""
from typing import List
import networkx as nx

from scdisrupt.agents.base import BaseAgent
from scdisrupt.common.types import Action, ActionType, NodeType
from scdisrupt.disruptions.cascade import CascadeAnalysis


class ProcurementAgent(BaseAgent):
    """Proposes switching suppliers, contracting secondary suppliers, and expediting component orders."""

    def __init__(self):
        super().__init__(name="Procurement Agent", role="Supplier sourcing and expediting")

    def propose_actions(self, graph: nx.DiGraph, cascade: CascadeAnalysis) -> List[Action]:
        actions: List[Action] = []

        # Find offline or degraded suppliers
        suppliers = [n for n, d in graph.nodes(data=True) if d.get("node_type") == NodeType.SUPPLIER]
        degraded = [s for s in suppliers if not graph.nodes[s].get("operational", True) or graph.nodes[s].get("daily_capacity", 0) <= 0]
        alternates = [s for s in suppliers if s not in degraded and graph.nodes[s].get("operational", True)]

        for deg_s in degraded:
            for alt_s in alternates:
                actions.append(
                    Action(
                        agent=self.name,
                        action_type=ActionType.SWITCH_SUPPLIER,
                        target_id=alt_s,
                        parameters={
                            "degraded_supplier": deg_s,
                            "target_supplier": alt_s,
                            "capacity_boost": 50.0,
                        },
                        estimated_cost=25000.0,
                        description=f"Shift sourcing from offline {deg_s} to backup supplier {alt_s} (+50 units/day capacity)",
                    )
                )

        # Propose expediting air freight from suppliers
        for s in alternates or suppliers:
            actions.append(
                Action(
                    agent=self.name,
                    action_type=ActionType.EXPEDITE_AIR,
                    target_id=s,
                    parameters={"speed_up_factor": 0.35, "cost_penalty": 3.0},
                    estimated_cost=35000.0,
                    description=f"Expedite supplier inbound freight via chartered air cargo from {s} (-65% lead time)",
                )
            )

        return actions
