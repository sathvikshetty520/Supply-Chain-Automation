"""Unit tests for Phase 2 discrete-event simulation core and Monte Carlo runs."""
from pathlib import Path
import pytest
import numpy as np

from scdisrupt.twin.loader import load_network_config, build_network_graph
from scdisrupt.simulation.model import SupplyChainSimulation
from scdisrupt.simulation.montecarlo import run_monte_carlo
from scdisrupt.simulation.distributions import sample_lead_time, sample_demand
from scdisrupt.common.seeds import get_rng


@pytest.fixture
def sample_graph():
    p = Path(__file__).parent.parent / "configs" / "sample_network.yaml"
    config = load_network_config(p)
    return build_network_graph(config)


def test_distribution_lead_time_and_demand():
    rng = get_rng(42)
    # Lead time should be positive and close to mean on average
    lead_times = [sample_lead_time(mean=10.0, std=2.0, rng=rng) for _ in range(1000)]
    assert np.mean(lead_times) > 8.0
    assert np.mean(lead_times) < 12.0
    assert all(lt >= 0.5 for lt in lead_times)

    # Customer demand should be non-negative
    demands = [sample_demand("normal", mean=25.0, std=5.0, rng=rng) for _ in range(500)]
    assert np.mean(demands) > 20.0
    assert np.mean(demands) < 30.0
    assert all(d >= 0.0 for d in demands)


def test_simulation_reproducibility(sample_graph):
    # Same seed must yield identical metrics
    sim1 = SupplyChainSimulation(sample_graph, seed=123, sim_duration_days=30)
    res1 = sim1.run()

    sim2 = SupplyChainSimulation(sample_graph, seed=123, sim_duration_days=30)
    res2 = sim2.run()

    assert res1.total_cost == res2.total_cost
    assert res1.total_revenue == res2.total_revenue
    assert res1.total_co2 == res2.total_co2
    assert res1.service_level == res2.service_level


def test_simulation_run_metrics(sample_graph):
    sim = SupplyChainSimulation(sample_graph, seed=42, sim_duration_days=45)
    res = sim.run()

    assert res.total_cost > 0.0
    assert res.total_revenue > 0.0
    assert 0.0 <= res.service_level <= 1.0
    assert len(res.daily_records) == 45


def test_monte_carlo_execution(sample_graph):
    mc_summary = run_monte_carlo(sample_graph, runs=10, base_seed=42, sim_duration_days=30)
    assert mc_summary.runs == 10
    assert mc_summary.mean_cost > 0.0
    assert mc_summary.p10_cost <= mc_summary.p90_cost
    assert 0.0 <= mc_summary.mean_service_level <= 1.0
    assert "WH_A" in mc_summary.node_stockout_probabilities
    assert "WH_B" in mc_summary.node_stockout_probabilities
