"""Executive briefing generator synthesizing incident summary, recovery decisions, and action plan."""
from typing import List, Optional
from scdisrupt.disruptions.cascade import CascadeAnalysis
from scdisrupt.scoring.counterfactual import PlanSimulationResult
from scdisrupt.scoring.scorer import ScoredPlan
from scdisrupt.explain.llm_client import LLMExplainerClient
from scdisrupt.explain.root_cause import RootCauseExplainer
from scdisrupt.explain.tradeoff import TradeoffExplainer


class ExecutiveBriefingGenerator:
    """Generates an end-to-end executive operations memo ready for C-suite decision-makers."""

    def __init__(self, client: Optional[LLMExplainerClient] = None):
        self.client = client or LLMExplainerClient()
        self.root_cause_explainer = RootCauseExplainer(self.client)
        self.tradeoff_explainer = TradeoffExplainer(self.client)

    def generate_briefing(
        self,
        cascade: CascadeAnalysis,
        scored_plans: List[ScoredPlan],
        pareto_plans: Optional[List[PlanSimulationResult]] = None,
    ) -> str:
        """Create a complete executive decision memo."""
        if not scored_plans:
            return "No recovery plans evaluated."

        top_plan = scored_plans[0]
        top_raw = top_plan.raw_result
        root_cause_text = self.root_cause_explainer.generate_narrative(cascade)
        tradeoff_text = self.tradeoff_explainer.generate_tradeoff_rationale(scored_plans, pareto_plans)

        action_items = []
        for i, act in enumerate(top_raw.plan.actions, 1):
            action_items.append(
                f"{i}. **[{act.agent.upper()}]** {act.description} "
                f"(Est. Cost: ${act.estimated_cost:,.2f}, Target: `{act.target_id}`)"
            )
        action_list_str = "\n".join(action_items) if action_items else "No immediate actions required."

        briefing = (
            f"# [INCIDENT RESPONSE BRIEFING]\n\n"
            f"**INCIDENT**: {cascade.disruption_name}\n"
            f"**STATUS**: Active Cascade Detected | Autonomous Recovery Plan Recommended\n\n"
            f"---\n\n"
            f"## 1. Executive Summary\n"
            f"A severe operational shock has occurred ({cascade.disruption_name}), jeopardizing **${cascade.revenue_at_risk:,.2f}** in potential revenue. "
            f"Without corrective intervention, network service levels drop from **{cascade.baseline_summary.mean_service_level * 100:.1f}%** "
            f"to **{cascade.disrupted_summary.mean_service_level * 100:.1f}%**.\n\n"
            f"The autonomous recovery orchestrator recommends **{top_plan.plan_name}** (Score: **{top_plan.final_score:.1f}/100**), "
            f"projected to restore service levels to **{top_raw.post_recovery_service_level * 100:.1f}%** with a net resilience factor of **{top_raw.resilience_score * 100:.1f}%**.\n\n"
            f"---\n\n"
            f"## 2. Root Cause & Disruption Dynamics\n"
            f"{root_cause_text}\n\n"
            f"---\n\n"
            f"## 3. Evaluated Recovery Strategies & Trade-Offs\n"
            f"{tradeoff_text}\n\n"
            f"---\n\n"
            f"## 4. Immediate Action Plan ({top_plan.plan_name})\n"
            f"The following intervention actions should be dispatched immediately:\n\n"
            f"{action_list_str}\n\n"
            f"- **Estimated Implementation Budget**: ${top_raw.action_cost:,.2f}\n"
            f"- **Expected Total Effective Cost**: ${top_raw.total_effective_cost:,.2f}\n"
            f"- **Projected Emissions**: {top_raw.post_recovery_co2:,.1f} kg CO2\n"
        )
        return briefing
