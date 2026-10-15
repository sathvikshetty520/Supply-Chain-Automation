"""Inventory Agent: handles safety stock dynamic buffering and regional pre-positioning."""
from typing import List
import networkx as nx

from scdisrupt.agents.base import BaseAgent
from scdisrupt.common.types import Action, ActionType, NodeType
from scdisrupt.disruptions.cascade import CascadeAnalysis


class InventoryAgent(BaseAgent):
    """Proposes dynamic safety stock adjustment and stock pre-positioning into vulnerable nodes."""

    def __init__(self):
        super().__init__(name="Inventory Agent", role="Buffer optimization and pre-positioning")

    def propose_actions(self, graph: nx.DiGraph, cascade: CascadeAnalysis) -> List[Action]:
        actions: List[Action] = []

        warehouses = [n for n, d in graph.nodes(data=True) if d.get("node_type") == NodeType.WAREHOUSE]

        # 1. Raise safety stock across vulnerable hubs
        for wh in warehouses:
            current_ss = graph.nodes[wh].get("safety_stock", 30.0)
            actions.append(
                Action(
                    agent=self.name,
                    action_type=ActionType.RAISE_SAFETY_STOCK,
                    target_id=wh,
                    parameters={"new_safety_stock": current_ss * 1.6, "multiplier": 1.6},
                    estimated_cost=15000.0,
                    description=f"Increase safety stock buffer at {wh} by +60% (to {int(current_ss * 1.6)} units)",
                )
            )

        # 2. Pre-position stock in Region B or earliest stockout warehouse
        target_wh = cascade.first_stockout_node if cascade.first_stockout_node in warehouses else ("WH_B" if "WH_B" in warehouses else warehouses[0])
        actions.append(
            Action(
                agent=self.name,
                action_type=ActionType.PREPOSITION_STOCK,
                target_id=target_wh,
                parameters={"preposition_quantity": 120.0},
                estimated_cost=20000.0,
                description=f"Pre-position 120 units of strategic reserve inventory directly into {target_wh}",
            )
        )

        return actions
