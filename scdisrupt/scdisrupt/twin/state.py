"""Twin state management: deep copy, snapshots, serialization and forking."""
import copy
from typing import Any, Dict
import networkx as nx


def snapshot_graph(G: nx.DiGraph) -> Dict[str, Any]:
    """Capture a serializable dictionary snapshot of graph node and edge attributes."""
    nodes_data = {n: copy.deepcopy(attrs) for n, attrs in G.nodes(data=True)}
    edges_data = [
        {"u": u, "v": v, "attrs": copy.deepcopy(attrs)}
        for u, v, attrs in G.edges(data=True)
    ]
    graph_attrs = copy.deepcopy(G.graph)
    return {
        "graph": graph_attrs,
        "nodes": nodes_data,
        "edges": edges_data,
    }


def fork_graph(G: nx.DiGraph) -> nx.DiGraph:
    """Create an isolated, independent deep copy of the digital twin graph."""
    return copy.deepcopy(G)


def restore_graph(snapshot: Dict[str, Any]) -> nx.DiGraph:
    """Reconstruct a NetworkX DiGraph from a previously captured snapshot."""
    G = nx.DiGraph(**snapshot.get("graph", {}))
    for node_id, attrs in snapshot.get("nodes", {}).items():
        G.add_node(node_id, **copy.deepcopy(attrs))
    for edge in snapshot.get("edges", []):
        G.add_edge(edge["u"], edge["v"], **copy.deepcopy(edge["attrs"]))
    return G
