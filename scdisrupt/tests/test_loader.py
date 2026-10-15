"""Unit tests for Phase 1 digital twin schema, loader, and state."""
from pathlib import Path
import pytest
import networkx as nx

from scdisrupt.twin.loader import load_network_config, build_network_graph
from scdisrupt.twin.state import fork_graph, snapshot_graph, restore_graph
from scdisrupt.common.types import NodeType


@pytest.fixture
def sample_yaml_path():
    p = Path(__file__).parent.parent / "configs" / "sample_network.yaml"
    return p


def test_load_sample_network_config(sample_yaml_path):
    config = load_network_config(sample_yaml_path)
    assert config.name == "Global Sample Supply Chain"
    assert len(config.suppliers) == 2
    assert len(config.factories) == 1
    assert len(config.warehouses) == 2
    assert len(config.customers) == 3
    assert len(config.lanes) == 7  # 2 sup->fac + 2 fac->wh + 3 wh->cust


def test_build_network_graph(sample_yaml_path):
    config = load_network_config(sample_yaml_path)
    G = build_network_graph(config)
    
    # 2 suppliers + 1 factory + 2 warehouses + 3 customers = 8 nodes
    assert G.number_of_nodes() == 8
    assert G.number_of_edges() == 7

    # Check node types
    suppliers = [n for n, d in G.nodes(data=True) if d.get("node_type") == NodeType.SUPPLIER]
    factories = [n for n, d in G.nodes(data=True) if d.get("node_type") == NodeType.FACTORY]
    warehouses = [n for n, d in G.nodes(data=True) if d.get("node_type") == NodeType.WAREHOUSE]
    customers = [n for n, d in G.nodes(data=True) if d.get("node_type") == NodeType.CUSTOMER]

    assert len(suppliers) == 2
    assert len(factories) == 1
    assert len(warehouses) == 2
    assert len(customers) == 3

    # Check edge attributes
    edge_data = G.get_edge_data("SUP_1", "FAC_1")
    assert edge_data is not None
    assert edge_data["lane_id"] == "LANE_SUP1_FAC1"
    assert edge_data["lead_time_mean"] == 4.0
    assert edge_data["cost_per_unit"] == 4.0


def test_graph_fork_and_isolation(sample_yaml_path):
    config = load_network_config(sample_yaml_path)
    G1 = build_network_graph(config)
    G2 = fork_graph(G1)

    # Modifying G2 must not affect G1
    G2.nodes["SUP_1"]["daily_capacity"] = 0.0
    G2.edges[("SUP_1", "FAC_1")]["disrupted"] = True

    assert G1.nodes["SUP_1"]["daily_capacity"] == 120.0
    assert G1.edges[("SUP_1", "FAC_1")]["disrupted"] is False


def test_graph_snapshot_and_restore(sample_yaml_path):
    config = load_network_config(sample_yaml_path)
    G = build_network_graph(config)
    snap = snapshot_graph(G)

    restored = restore_graph(snap)
    assert restored.number_of_nodes() == G.number_of_nodes()
    assert restored.number_of_edges() == G.number_of_edges()
    assert restored.nodes["FAC_1"]["daily_capacity"] == G.nodes["FAC_1"]["daily_capacity"]
