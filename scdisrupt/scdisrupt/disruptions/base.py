"""Base interface for digital twin disruptions."""
from abc import ABC, abstractmethod
from typing import Any, Dict
import networkx as nx

from scdisrupt.twin.state import fork_graph


class Disruption(ABC):
    """Abstract base class for all supply-chain disruption injectors."""

    def __init__(self, name: str, description: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.parameters = parameters or {}

    @abstractmethod
    def apply(self, graph: nx.DiGraph) -> nx.DiGraph:
        """Apply disruption to a forked twin graph, returning the modified graph."""
        pass
