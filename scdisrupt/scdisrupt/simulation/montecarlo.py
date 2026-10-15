"""Monte Carlo simulation runner computing distributions, percentiles, and stockout probabilities."""
from typing import List, Optional
import networkx as nx
import numpy as np

from scdisrupt.common.types import MonteCarloSummary, RunMetrics
from scdisrupt.simulation.model import SupplyChainSimulation
from scdisrupt.twin.state import fork_graph


def run_monte_carlo(
    graph: nx.DiGraph,
    runs: int = 50,
    base_seed: int = 42,
    sim_duration_days: int = 60,
) -> MonteCarloSummary:
    """Run Monte Carlo simulation across multiple randomized seeds and compute aggregate stats."""
    run_results: List[RunMetrics] = []
    node_stockout_counts = {nid: 0 for nid in graph.nodes()}

    for i in range(runs):
        seed = base_seed + i * 17
        twin_copy = fork_graph(graph)
        sim = SupplyChainSimulation(twin_copy, seed=seed, sim_duration_days=sim_duration_days)
        result = sim.run()
        run_results.append(result)

        for snode in result.stockout_nodes:
            if snode in node_stockout_counts:
                node_stockout_counts[snode] += 1

    costs = [r.total_cost for r in run_results]
    service_levels = [r.service_level for r in run_results]
    co2s = [r.total_co2 for r in run_results]
    
    # Revenue at risk: difference between theoretical max revenue and actual revenue
    revenues = [r.total_revenue for r in run_results]
    max_rev = max(revenues) if revenues else 0.0
    revenue_at_risk = [max_rev - rev for rev in revenues]

    node_stockout_probs = {
        nid: float(np.round(count / runs, 4))
        for nid, count in node_stockout_counts.items()
        if graph.nodes[nid].get("node_type") != "supplier"  # focus on warehouses/customers/factories
    }

    return MonteCarloSummary(
        runs=runs,
        mean_cost=float(np.round(np.mean(costs), 2)),
        p10_cost=float(np.round(np.percentile(costs, 10), 2)),
        p90_cost=float(np.round(np.percentile(costs, 90), 2)),
        mean_service_level=float(np.round(np.mean(service_levels), 4)),
        p10_service_level=float(np.round(np.percentile(service_levels, 10), 4)),
        p90_service_level=float(np.round(np.percentile(service_levels, 90), 4)),
        mean_co2=float(np.round(np.mean(co2s), 2)),
        node_stockout_probabilities=node_stockout_probs,
        mean_revenue_at_risk=float(np.round(np.mean(revenue_at_risk), 2)),
        runs_details=run_results,
    )
