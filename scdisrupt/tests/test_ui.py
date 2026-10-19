"""Smoke and functional tests for the Streamlit dashboard components."""
import sys
from pathlib import Path
import pytest
import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scdisrupt.twin.loader import load_network_config, build_network_graph
from scdisrupt.disruptions.catalog import PortStrikeDisruption
from scdisrupt.disruptions.cascade import analyze_cascade
from scdisrupt.agents.orchestrator import AgentOrchestrator
from scdisrupt.scoring.counterfactual import evaluate_counterfactual_plans
from scdisrupt.scoring.scorer import PlanScorer
from scdisrupt.scoring.pareto import get_pareto_plans
from scdisrupt.explain.briefing import ExecutiveBriefingGenerator


@pytest.fixture
def sample_config_path():
    return Path(__file__).parent.parent / "configs" / "sample_network.yaml"


def test_ui_data_pipeline_flow(sample_config_path):
    """Validate that the exact data pipeline utilized by the UI runs cleanly."""
    config = load_network_config(sample_config_path)
    graph = build_network_graph(config)
    assert graph.number_of_nodes() > 0

    # Build node and lane structures as formatted in the UI
    node_rows = []
    for nid, d in graph.nodes(data=True):
        inv = d.get("inventory_policy")
        node_rows.append(
            {
                "Node ID": nid,
                "Name": d.get("name", nid),
                "Type": d.get("type", "unknown").capitalize(),
                "Initial Inventory": inv.initial_inventory if inv else "-",
            }
        )
    df_nodes = pd.DataFrame(node_rows)
    assert not df_nodes.empty

    disruption = PortStrikeDisruption(lead_time_multiplier=2.5)
    cascade = analyze_cascade(graph, disruption, runs=2, sim_duration_days=15, base_seed=42)
    assert cascade is not None

    orchestrator = AgentOrchestrator()
    plans = orchestrator.formulate_plans(graph, cascade)
    assert len(plans) > 0

    results = evaluate_counterfactual_plans(graph, plans, runs=2, sim_duration_days=15, base_seed=42)
    scorer = PlanScorer()
    scored = scorer.score_plans(results)
    assert len(scored) == len(plans)

    pareto = get_pareto_plans(results)
    assert len(pareto) > 0

    gen = ExecutiveBriefingGenerator()
    briefing = gen.generate_briefing(cascade, scored, pareto)
    assert "EXECUTIVE INCIDENT RESPONSE BRIEFING" in briefing
