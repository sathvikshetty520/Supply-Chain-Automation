"""Unit tests for Phase 4 multi-agent recovery proposals and LP optimizer."""
from pathlib import Path
import pytest

from scdisrupt.twin.loader import load_network_config, build_network_graph
from scdisrupt.disruptions.catalog import SupplierFailureDisruption
from scdisrupt.disruptions.cascade import analyze_cascade
from scdisrupt.agents.orchestrator import AgentOrchestrator
from scdisrupt.optimizer.allocation import solve_least_cost_allocation


@pytest.fixture
def sample_graph():
    p = Path(__file__).parent.parent / "configs" / "sample_network.yaml"
    config = load_network_config(p)
    return build_network_graph(config)


def test_agent_orchestrator_plans(sample_graph):
    disruption = SupplierFailureDisruption(supplier_id="SUP_1", capacity_reduction=1.0)
    cascade = analyze_cascade(sample_graph, disruption, runs=3, sim_duration_days=20, base_seed=42)

    orchestrator = AgentOrchestrator()
    plans = orchestrator.formulate_plans(sample_graph, cascade)

    assert len(plans) == 3
    plan_ids = [p.id for p in plans]
    assert "PLAN_A" in plan_ids
    assert "PLAN_B" in plan_ids
    assert "PLAN_C" in plan_ids

    for p in plans:
        assert len(p.actions) > 0
        assert p.budget_limit is not None


def test_pulp_least_cost_optimizer(sample_graph):
    disruption = SupplierFailureDisruption(supplier_id="SUP_1", capacity_reduction=1.0)
    disrupted_graph = disruption.apply(sample_graph)
    cascade = analyze_cascade(sample_graph, disruption, runs=3, sim_duration_days=20, base_seed=42)

    orchestrator = AgentOrchestrator()
    plans = orchestrator.formulate_plans(disrupted_graph, cascade)

    flows = solve_least_cost_allocation(disrupted_graph, plans[0])
    assert isinstance(flows, dict)
    assert len(flows) > 0
    assert all(val >= 0.0 for val in flows.values())
