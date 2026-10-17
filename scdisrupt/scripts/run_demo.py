"""End-to-end demonstration script of the Autonomous Supply-Chain Disruption Simulator (scdisrupt)."""
import argparse
from pathlib import Path
import sys

# Ensure package root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scdisrupt.twin.loader import load_network_config, build_network_graph
from scdisrupt.disruptions.catalog import (
    SupplierFailureDisruption,
    PortStrikeDisruption,
    DemandSurgeDisruption,
    CurrencyShockDisruption,
)
from scdisrupt.disruptions.cascade import analyze_cascade
from scdisrupt.agents.orchestrator import AgentOrchestrator
from scdisrupt.scoring.counterfactual import evaluate_counterfactual_plans
from scdisrupt.scoring.scorer import PlanScorer
from scdisrupt.scoring.pareto import get_pareto_plans
from scdisrupt.explain.briefing import ExecutiveBriefingGenerator


def run_pipeline(
    config_path: Path,
    disruption_type: str = "port_strike",
    runs: int = 5,
    sim_days: int = 45,
    seed: int = 42,
):
    print("=" * 80)
    print(">> SC-DISRUPT: AUTONOMOUS SUPPLY CHAIN DISRUPTION SIMULATOR & DIGITAL TWIN")
    print("=" * 80)

    # 1. Load Digital Twin
    print(f"\n[1/6] Loading Digital Twin network from '{config_path}'...")
    config = load_network_config(config_path)
    graph = build_network_graph(config)
    print(f"      Loaded '{config.name}' with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} transport lanes.")

    # 2. Configure Disruption Shock
    print(f"\n[2/6] Triggering disruption scenario: '{disruption_type}'...")
    if disruption_type == "port_strike":
        disruption = PortStrikeDisruption(lead_time_multiplier=3.0)
    elif disruption_type == "supplier_failure":
        disruption = SupplierFailureDisruption(supplier_id="SUP_1", capacity_reduction=1.0)
    elif disruption_type == "demand_surge":
        disruption = DemandSurgeDisruption(surge_factor=1.4)
    elif disruption_type == "currency_shock":
        disruption = CurrencyShockDisruption(cost_multiplier=1.25)
    else:
        print(f"Unknown disruption type '{disruption_type}', defaulting to Port Strike.")
        disruption = PortStrikeDisruption(lead_time_multiplier=3.0)

    # 3. Simulate Cascade Propagation
    print(f"\n[3/6] Running Monte Carlo cascade simulation ({runs} runs, {sim_days} days horizon)...")
    cascade = analyze_cascade(graph, disruption, runs=runs, sim_duration_days=sim_days, base_seed=seed)
    print(f"      Baseline Service Level: {cascade.baseline_summary.mean_service_level * 100:.1f}%")
    print(f"      Disrupted Service Level: {cascade.disrupted_summary.mean_service_level * 100:.1f}%")
    print(f"      Revenue at Risk: ${cascade.revenue_at_risk:,.2f}")
    print(f"      Cost Impact Delta: ${cascade.cost_delta:+,.2f}")
    if cascade.first_stockout_node:
        print(f"      Earliest Failure Node: '{cascade.first_stockout_node}' on Day {cascade.first_stockout_day}")

    # 4. Multi-Agent Recovery Plan Generation
    print("\n[4/6] Formulating multi-agent recovery proposals...")
    orchestrator = AgentOrchestrator()
    plans = orchestrator.formulate_plans(graph, cascade)
    for p in plans:
        print(f"      -> Generated {p.name}: {len(p.actions)} actions (Budget Cap: ${p.budget_limit:,.0f})")

    # 5. Counterfactual Simulation, Scorer & Pareto Optimization
    print(f"\n[5/6] Simulating candidate plans counterfactually and computing Pareto frontier...")
    results = evaluate_counterfactual_plans(graph, plans, runs=runs, sim_duration_days=sim_days, base_seed=seed)
    scorer = PlanScorer(weight_cost=0.35, weight_service_level=0.35, weight_co2=0.15, weight_resilience=0.15)
    scored_plans = scorer.score_plans(results)
    pareto_plans = get_pareto_plans(results)
    pareto_ids = {p.plan.id for p in pareto_plans}

    print("\n" + "-" * 82)
    print(f"{'Rank':<6}{'Plan Name':<34}{'Score':<10}{'Cost ($)':<14}{'Service':<12}{'Pareto'}")
    print("-" * 82)
    for sp in scored_plans:
        r = sp.raw_result
        is_p = "YES" if sp.plan_id in pareto_ids else "NO"
        service_pct = f"{r.post_recovery_service_level * 100:.1f}%"
        print(
            f"#{sp.rank:<5}{sp.plan_name:<34}{sp.final_score:<10.1f}"
            f"${r.total_effective_cost:<13,.0f}{service_pct:<12}{is_p}"
        )
    print("-" * 82)

    # 6. Executive Explanation & Briefing
    print("\n[6/6] Generating Executive Incident Response Memo...")
    briefing_gen = ExecutiveBriefingGenerator()
    briefing = briefing_gen.generate_briefing(cascade, scored_plans, pareto_plans)

    print("\n" + briefing)
    print("\n" + "=" * 80)
    print("[SUCCESS] Pipeline completed successfully.")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SC-Disrupt End-to-End Execution Demo")
    parser.add_argument(
        "--config",
        type=str,
        default=str(Path(__file__).parent.parent / "configs" / "sample_network.yaml"),
        help="Path to network YAML configuration file",
    )
    parser.add_argument(
        "--disruption",
        type=str,
        default="port_strike",
        choices=["port_strike", "supplier_failure", "demand_surge", "currency_shock"],
        help="Disruption type to apply",
    )
    parser.add_argument("--runs", type=int, default=5, help="Number of Monte Carlo runs")
    parser.add_argument("--days", type=int, default=45, help="Simulation duration in days")
    parser.add_argument("--seed", type=int, default=42, help="Random base seed")

    args = parser.parse_args()
    run_pipeline(
        config_path=Path(args.config),
        disruption_type=args.disruption,
        runs=args.runs,
        sim_days=args.days,
        seed=args.seed,
    )
