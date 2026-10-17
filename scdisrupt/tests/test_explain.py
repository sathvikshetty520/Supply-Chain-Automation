"""Unit tests for Phase 6 LLM explanation and executive briefing generator."""
from pathlib import Path
import pytest

from scdisrupt.twin.loader import load_network_config, build_network_graph
from scdisrupt.disruptions.catalog import PortStrikeDisruption
from scdisrupt.disruptions.cascade import analyze_cascade
from scdisrupt.agents.orchestrator import AgentOrchestrator
from scdisrupt.scoring.counterfactual import evaluate_counterfactual_plans
from scdisrupt.scoring.scorer import PlanScorer
from scdisrupt.scoring.pareto import get_pareto_plans
from scdisrupt.explain.root_cause import RootCauseExplainer
from scdisrupt.explain.tradeoff import TradeoffExplainer
from scdisrupt.explain.briefing import ExecutiveBriefingGenerator


@pytest.fixture
def sample_graph():
    p = Path(__file__).parent.parent / "configs" / "sample_network.yaml"
    config = load_network_config(p)
    return build_network_graph(config)


def test_root_cause_explainer(sample_graph):
    disruption = PortStrikeDisruption(lead_time_multiplier=3.0)
    cascade = analyze_cascade(sample_graph, disruption, runs=3, sim_duration_days=20, base_seed=42)

    explainer = RootCauseExplainer()
    narrative = explainer.generate_narrative(cascade)

    assert isinstance(narrative, str)
    assert len(narrative) > 100
    assert "Root-Cause" in narrative or "Port Strike" in narrative


def test_tradeoff_explainer(sample_graph):
    disruption = PortStrikeDisruption(lead_time_multiplier=3.0)
    cascade = analyze_cascade(sample_graph, disruption, runs=3, sim_duration_days=20, base_seed=42)

    orchestrator = AgentOrchestrator()
    plans = orchestrator.formulate_plans(sample_graph, cascade)

    results = evaluate_counterfactual_plans(sample_graph, plans, runs=3, sim_duration_days=20, base_seed=42)
    scorer = PlanScorer()
    scored = scorer.score_plans(results)
    pareto = get_pareto_plans(results)

    tradeoff_gen = TradeoffExplainer()
    text = tradeoff_gen.generate_tradeoff_rationale(scored, pareto)

    assert isinstance(text, str)
    assert len(text) > 100
    assert "PLAN_" in text or "Plan" in text


def test_executive_briefing_generator(sample_graph):
    disruption = PortStrikeDisruption(lead_time_multiplier=3.0)
    cascade = analyze_cascade(sample_graph, disruption, runs=3, sim_duration_days=20, base_seed=42)

    orchestrator = AgentOrchestrator()
    plans = orchestrator.formulate_plans(sample_graph, cascade)

    results = evaluate_counterfactual_plans(sample_graph, plans, runs=3, sim_duration_days=20, base_seed=42)
    scorer = PlanScorer()
    scored = scorer.score_plans(results)
    pareto = get_pareto_plans(results)

    briefing_gen = ExecutiveBriefingGenerator()
    briefing = briefing_gen.generate_briefing(cascade, scored, pareto)

    assert isinstance(briefing, str)
    assert "EXECUTIVE INCIDENT RESPONSE BRIEFING" in briefing
    assert "Immediate Action Plan" in briefing
    assert len(briefing) > 300
