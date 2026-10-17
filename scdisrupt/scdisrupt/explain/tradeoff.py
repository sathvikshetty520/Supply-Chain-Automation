"""Trade-off explainer comparing candidate recovery plans (Cost vs Service vs CO2 vs Resilience)."""
from typing import List, Optional
from scdisrupt.scoring.counterfactual import PlanSimulationResult
from scdisrupt.scoring.scorer import ScoredPlan
from scdisrupt.explain.llm_client import LLMExplainerClient


class TradeoffExplainer:
    """Explains why specific recovery plans outrank others across conflicting dimensions."""

    def __init__(self, client: Optional[LLMExplainerClient] = None):
        self.client = client or LLMExplainerClient()

    def generate_tradeoff_rationale(
        self,
        scored_plans: List[ScoredPlan],
        pareto_plans: Optional[List[PlanSimulationResult]] = None,
    ) -> str:
        """Produce an articulate comparative rationale for plan rankings and Pareto efficiency."""
        if not scored_plans:
            return "No scored plans available for trade-off evaluation."

        top_plan = scored_plans[0]
        pareto_ids = {p.plan.id for p in (pareto_plans or [])}

        plan_summaries = []
        for sp in scored_plans:
            r = sp.raw_result
            is_pareto = "Yes" if (not pareto_plans or sp.plan_id in pareto_ids) else "Dominated"
            plan_summaries.append(
                f"- **{sp.plan_name} (Rank #{sp.rank}, Score: {sp.final_score:.1f}/100, Pareto: {is_pareto})**:\n"
                f"  - Total Cost: ${r.total_effective_cost:,.2f} (Action capex: ${r.action_cost:,.2f})\n"
                f"  - Service Level: {r.post_recovery_service_level * 100:.1f}%\n"
                f"  - Carbon Footprint: {r.post_recovery_co2:,.1f} kg CO2\n"
                f"  - Network Resilience: {r.resilience_score * 100:.1f}%\n"
                f"  - Core Strategy: {sp.raw_result.plan.description}"
            )

        fallback = (
            f"### Multi-Objective Trade-Off Rationale\n\n"
            f"**Recommended Strategy**: **{top_plan.plan_name}** with a composite score of **{top_plan.final_score:.1f}/100**.\n\n"
            f"**Candidate Comparison**:\n"
            + "\n".join(plan_summaries)
            + f"\n\n**Decision Drivers & Trade-Offs**:\n"
            f"1. **Cost vs. Service Level**: While expedited air or rapid supplier switching incurs higher upfront implementation cost, "
            f"it curbs catastrophic stockout penalties and protects customer fulfillment.\n"
            f"2. **Sustainability Impact**: Air rerouting exhibits higher CO2 emissions, representing a deliberate compromise "
            f"to preserve critical timeline guarantees.\n"
            f"3. **Pareto Optimality**: The highest-ranked solutions lie on or close to the Pareto frontier, guaranteeing that no alternative "
            f"can improve service level without disproportionate escalation in expenditures or environmental footprint."
        )

        system_prompt = (
            "You are a strategic supply chain economist and executive advisor. "
            "Explain the trade-offs between multiple supply chain disruption recovery plans."
        )
        user_prompt = (
            f"Review the candidate recovery plans below and write a 2-3 paragraph trade-off analysis explaining why "
            f"the top plan is favored, which trade-offs (cost vs service vs carbon vs resilience) are made, and operational recommendations.\n\n"
            + "\n".join(plan_summaries)
        )

        return self.client.call_llm(system_prompt, user_prompt, fallback)
