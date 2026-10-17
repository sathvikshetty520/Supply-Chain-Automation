"""Root cause narrative generator explaining disruption propagation and cascade impact."""
from typing import Optional
from scdisrupt.disruptions.cascade import CascadeAnalysis
from scdisrupt.explain.llm_client import LLMExplainerClient


class RootCauseExplainer:
    """Produces clear natural language root-cause analysis from CascadeAnalysis data."""

    def __init__(self, client: Optional[LLMExplainerClient] = None):
        self.client = client or LLMExplainerClient()

    def generate_narrative(self, cascade: CascadeAnalysis) -> str:
        """Generate human-readable root-cause and propagation cascade summary."""
        # Structured fallback narrative
        top_vulnerable = (
            ", ".join([
                f"{item.get('node_name', item.get('node_id', 'Unknown'))} ({item.get('disrupted_prob', item.get('stockout_probability', 0.0)) * 100:.0f}%)"
                for item in cascade.vulnerable_nodes_ranked[:3]
            ])
            if cascade.vulnerable_nodes_ranked
            else "None identified"
        )
        
        first_stockout_desc = (
            f"Node '{cascade.first_stockout_node}' on Day {cascade.first_stockout_day}"
            if cascade.first_stockout_node
            else "No stockout recorded"
        )

        fallback = (
            f"### Root-Cause Disruption & Propagation Analysis\n"
            f"- **Disruption Event**: {cascade.disruption_name}\n"
            f"- **First Node Stockout**: {first_stockout_desc}\n"
            f"- **Service Level Degradation**: Dropped from {cascade.baseline_summary.mean_service_level * 100:.1f}% "
            f"to {cascade.disrupted_summary.mean_service_level * 100:.1f}% ({cascade.service_level_delta * 100:+.1f}% points)\n"
            f"- **Revenue at Risk**: ${cascade.revenue_at_risk:,.2f} over the evaluation horizon\n"
            f"- **Total Operational Cost Increase**: ${cascade.cost_delta:+,.2f} ({(cascade.cost_delta / max(1.0, cascade.baseline_summary.mean_cost)) * 100:+.1f}%)\n"
            f"- **Most Vulnerable Downstream Nodes**: {top_vulnerable}\n\n"
            f"**Propagation Mechanism**:\n"
            f"The initial failure rapidly starved intermediate buffer inventories. As safety thresholds depleted, "
            f"upstream supply constraints cascaded downstream, triggering fulfillment bottlenecks at regional distribution hubs."
        )

        system_prompt = (
            "You are an expert supply chain risk and resilience analyst. "
            "Write a concise, professional root-cause executive breakdown of a supply chain disruption."
        )
        user_prompt = (
            f"Disruption Name: {cascade.disruption_name}\n"
            f"First Stockout: Node {cascade.first_stockout_node} on day {cascade.first_stockout_day}\n"
            f"Baseline Service Level: {cascade.baseline_summary.mean_service_level*100:.1f}%, Disrupted: {cascade.disrupted_summary.mean_service_level*100:.1f}%\n"
            f"Revenue at Risk: ${cascade.revenue_at_risk:,.2f}\n"
            f"Operational Cost Delta: ${cascade.cost_delta:+,.2f}\n"
            f"Vulnerable Nodes: {top_vulnerable}\n\n"
            f"Please synthesize this into a clear 2-paragraph narrative highlighting root cause, propagation velocity, and critical failure points."
        )

        return self.client.call_llm(system_prompt, user_prompt, fallback)
