"""Base agent interface for supply chain recovery strategies."""
from abc import ABC, abstractmethod
from typing import List
import networkx as nx

from scdisrupt.common.types import Action
from scdisrupt.disruptions.cascade import CascadeAnalysis


class BaseAgent(ABC):
    """Abstract base class for domain-specific recovery agents."""

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    @abstractmethod
    def propose_actions(self, graph: nx.DiGraph, cascade: CascadeAnalysis) -> List[Action]:
        """Analyze current disrupted graph and cascade, proposing recovery actions."""
        pass
