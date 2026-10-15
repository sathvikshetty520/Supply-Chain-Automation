"""Routing Agent: evaluates transportation modal shifts and lane rerouting."""
from typing import List
import networkx as nx

from scdisrupt.agents.base import BaseAgent
from scdisrupt.common.types import Action, ActionType
from scdisrupt.disruptions.cascade import CascadeAnalysis


class RoutingAgent(BaseAgent):
    """Proposes transport mode switching (e.g. ocean -> air/rail) and bottleneck bypass."""

    def __init__(self):
        super().__init__(name="Routing Agent", role="Modal shifts and lane rerouting")

    def propose_actions(self, graph: nx.DiGraph, cascade: CascadeAnalysis) -> List[Action]:
        actions: List[Action] = []

        # Find long or disrupted lanes
        for u, v, attrs in graph.edges(data=True):
            lane_id = attrs.get("lane_id", f"{u}_{v}")
            mode = attrs.get("mode", "ocean")
            lt_mult = attrs.get("lead_time_multiplier", 1.0)

            if mode == "ocean" or lt_mult > 1.5:
                # Propose air cargo bypass
                actions.append(
                    Action(
                        agent=self.name,
                        action_type=ActionType.REROUTE_LANE,
                        target_id=lane_id,
                        parameters={
                            "origin": u,
                            "destination": v,
                            "new_mode": "air",
                            "lead_time_reduction": 0.30,  # 70% faster
                            "cost_multiplier": 2.8,
                            "co2_multiplier": 3.5,
                        },
                        estimated_cost=30000.0,
                        description=f"Switch lane {lane_id} ({u} -> {v}) from {mode} to Air Freight (slashes lead time by 70%)",
                    )
                )

        return actions
