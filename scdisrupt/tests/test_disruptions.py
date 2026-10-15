"""Unit tests for Phase 3 disruption catalog and cascading failure analysis."""
from pathlib import Path
import pytest

from scdisrupt.twin.loader import load_network_config, build_network_graph
from scdisrupt.disruptions.catalog import (
    SupplierFailureDisruption,
    PortStrikeDisruption,
    CurrencyShockDisruption,
    DemandSurgeDisruption,
)
from scdisrupt.disruptions.cascade import analyze_cascade


@pytest.fixture
def sample_graph():
    p = Path(__file__).parent.parent / "configs" / "sample_network.yaml"
    config = load_network_config(p)
    return build_network_graph(config)


def test_supplier_failure_disruption(sample_graph):
    disruption = SupplierFailureDisruption(supplier_id="SUP_1", capacity_reduction=1.0)
    disrupted = disruption.apply(sample_graph)
    
    assert disrupted.nodes["SUP_1"]["daily_capacity"] == 0.0
    assert disrupted.nodes["SUP_1"]["operational"] is False
    # Ensure baseline wasn't modified
    assert sample_graph.nodes["SUP_1"]["daily_capacity"] > 0.0


def test_port_strike_disruption(sample_graph):
    disruption = PortStrikeDisruption(lead_time_multiplier=3.0)
    disrupted = disruption.apply(sample_graph)

    # Ocean lane lead times should be tripled
    ocean_edge = disrupted.edges[("FAC_1", "WH_A")]
    assert ocean_edge["lead_time_multiplier"] == 3.0
    assert ocean_edge["disrupted"] is True


def test_currency_shock_disruption(sample_graph):
    disruption = CurrencyShockDisruption(cost_multiplier=1.25)
    disrupted = disruption.apply(sample_graph)

    assert disrupted.nodes["SUP_1"]["unit_cost"] == sample_graph.nodes["SUP_1"]["unit_cost"] * 1.25
    assert disrupted.edges[("WH_A", "CUST_1")]["cost_multiplier"] == 1.25


def test_demand_surge_disruption(sample_graph):
    disruption = DemandSurgeDisruption(surge_factor=1.4)
    disrupted = disruption.apply(sample_graph)

    assert disrupted.nodes["CUST_1"]["demand_mean"] == sample_graph.nodes["CUST_1"]["demand_mean"] * 1.4


def test_cascade_analysis_runner(sample_graph):
    disruption = SupplierFailureDisruption(supplier_id="SUP_1", capacity_reduction=1.0)
    cascade = analyze_cascade(sample_graph, disruption, runs=5, sim_duration_days=30, base_seed=42)

    assert cascade.disrupted_summary.runs == 5
    assert cascade.baseline_summary.runs == 5
    assert cascade.revenue_at_risk >= 0.0
    assert isinstance(cascade.vulnerable_nodes_ranked, list)
    assert len(cascade.vulnerable_nodes_ranked) > 0
