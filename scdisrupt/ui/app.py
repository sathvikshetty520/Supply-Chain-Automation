"""Streamlit interactive dashboard for SC-Disrupt: Autonomous Supply-Chain Disruption Simulator & Digital Twin."""
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Also ensure scdisrupt root is on sys.path
SCDISRUPT_ROOT = Path(__file__).parent.parent
if str(SCDISRUPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCDISRUPT_ROOT))

from scdisrupt.twin.loader import load_network_config, build_network_graph
from scdisrupt.disruptions.catalog import (
    PortStrikeDisruption,
    SupplierFailureDisruption,
    DemandSurgeDisruption,
    CurrencyShockDisruption,
)
from scdisrupt.disruptions.cascade import analyze_cascade
from scdisrupt.agents.orchestrator import AgentOrchestrator
from scdisrupt.scoring.counterfactual import evaluate_counterfactual_plans
from scdisrupt.scoring.scorer import PlanScorer
from scdisrupt.scoring.pareto import get_pareto_plans
from scdisrupt.explain.briefing import ExecutiveBriefingGenerator

# Page configuration
st.set_page_config(
    page_title="SC-Disrupt | Autonomous Supply Chain Twin",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E293B;
    }
    .metric-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        color: #64748B;
        letter-spacing: 0.05em;
    }
    .badge-pareto {
        background-color: #10B981;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-dominated {
        background-color: #94A3B8;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DEFAULT_CONFIG_PATH = SCDISRUPT_ROOT / "configs" / "sample_network.yaml"


@st.cache_data
def get_graph(config_path_str: str):
    cfg = load_network_config(Path(config_path_str))
    g = build_network_graph(cfg)
    return cfg, g


# Sidebar Controls
st.sidebar.image("https://img.icons8.com/fluency/96/supply-chain.png", width=64)
st.sidebar.title("Simulation Controls")

config_file = st.sidebar.text_input("Config Path", str(DEFAULT_CONFIG_PATH))

try:
    config, graph = get_graph(config_file)
except Exception as e:
    st.sidebar.error(f"Failed to load config: {e}")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.subheader("Disruption Shock Injection")

disruption_type = st.sidebar.selectbox(
    "Disruption Type",
    options=["Port Strike", "Supplier Failure", "Demand Surge", "Currency Shock"],
    index=0,
)

if disruption_type == "Port Strike":
    lt_mult = st.sidebar.slider("Lead Time Multiplier", 1.5, 6.0, 3.0, 0.5)
    disruption = PortStrikeDisruption(lead_time_multiplier=lt_mult)
elif disruption_type == "Supplier Failure":
    supp_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "supplier"]
    sel_supplier = st.sidebar.selectbox("Failing Supplier", options=supp_nodes if supp_nodes else ["SUP_1"])
    cap_red = st.sidebar.slider("Capacity Reduction", 0.1, 1.0, 1.0, 0.1)
    disruption = SupplierFailureDisruption(supplier_id=sel_supplier, capacity_reduction=cap_red)
elif disruption_type == "Demand Surge":
    surge_f = st.sidebar.slider("Surge Factor", 1.1, 3.0, 1.4, 0.1)
    disruption = DemandSurgeDisruption(surge_factor=surge_f)
else:
    cost_m = st.sidebar.slider("Cost Multiplier", 1.1, 2.5, 1.25, 0.05)
    disruption = CurrencyShockDisruption(cost_multiplier=cost_m)

st.sidebar.markdown("---")
st.sidebar.subheader("Simulation Parameters")
runs = st.sidebar.slider("Monte Carlo Runs", 1, 20, 5, 1)
sim_days = st.sidebar.slider("Horizon (Days)", 15, 90, 45, 5)
random_seed = st.sidebar.number_input("Random Seed", value=42, step=1)

run_button = st.sidebar.button("Run Simulation & Recovery", type="primary", use_container_width=True)

# Main Title & Subtitle
st.markdown('<div class="main-title">SC-Disrupt: Autonomous Supply-Chain Twin</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Real-time discrete-event cascade modeling, autonomous multi-agent recovery, Pareto trade-off analysis, and GenAI executive briefings.</div>',
    unsafe_allow_html=True,
)

tab_overview, tab_cascade, tab_recovery, tab_pareto, tab_briefing = st.tabs(
    ["Topology & Twin", "Cascade Analysis", "Autonomous Recovery Plans", "Pareto Frontier", "Executive Memo"]
)

# Tab 1: Topology
with tab_overview:
    st.subheader("Digital Twin Network Topology")
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        st.metric("Total Nodes", graph.number_of_nodes())
    with col_t2:
        st.metric("Active Transport Lanes", graph.number_of_edges())
    with col_t3:
        st.metric("Currencies", len(config.currencies))
    with col_t4:
        st.metric("Products Tracked", len(config.products))

    # Network Node Table
    node_rows = []
    for nid, d in graph.nodes(data=True):
        inv = d.get("inventory_policy")
        node_rows.append(
            {
                "Node ID": nid,
                "Name": d.get("name", nid),
                "Type": d.get("type", "unknown").capitalize(),
                "Location": d.get("location", ""),
                "Initial Inventory": inv.initial_inventory if inv else "-",
                "Safety Stock": inv.safety_stock if inv else "-",
                "Max Capacity": inv.capacity if inv else d.get("daily_capacity", "-"),
            }
        )
    df_nodes = pd.DataFrame(node_rows)

    lane_rows = []
    for u, v, d in graph.edges(data=True):
        lane_rows.append(
            {
                "Origin": u,
                "Destination": v,
                "Transport Mode": d.get("mode", "ocean").upper(),
                "Lead Time (Days)": d.get("lead_time_mean", 1.0),
                "Unit Cost ($)": d.get("cost_per_unit", 1.0),
                "Capacity (units/day)": d.get("capacity", 100.0),
                "CO2 (kg/unit)": d.get("co2_per_unit", 1.0),
            }
        )
    df_lanes = pd.DataFrame(lane_rows)

    c_left, c_right = st.columns([1, 1])
    with c_left:
        st.write("**Nodes & Facilities**")
        st.dataframe(df_nodes, use_container_width=True, hide_index=True)
    with c_right:
        st.write("**Transportation Lanes & Lead Times**")
        st.dataframe(df_lanes, use_container_width=True, hide_index=True)

    # Topology Graph Visual
    st.write("**Interactive Graph Layout**")
    import networkx as nx
    try:
        pos = nx.spring_layout(graph, seed=42, k=1.2)
    except Exception:
        pos = {n: (i, i % 3) for i, n in enumerate(graph.nodes())}
    
    edge_x = []
    edge_y = []
    for u, v in graph.edges():
        x0, y0 = pos.get(u, (0.0, 0.0))
        x1, y1 = pos.get(v, (1.0, 1.0))
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color="#94A3B8"),
        hoverinfo="none",
        mode="lines",
    )

    node_x = []
    node_y = []
    node_text = []
    node_colors = []
    color_scheme = {
        "supplier": "#3B82F6",
        "factory": "#EC4899",
        "warehouse": "#8B5CF6",
        "customer": "#10B981",
        "port": "#F59E0B",
        "dc": "#8B5CF6",
    }
    for nid, d in graph.nodes(data=True):
        x, y = pos.get(nid, (0.5, 0.5))
        node_x.append(x)
        node_y.append(y)
        ntype = str(d.get("type", "")).lower()
        node_text.append(f"<b>{nid}</b> ({ntype})<br>{d.get('name', '')}<br>Location: {d.get('location', 'N/A')}")
        node_colors.append(color_scheme.get(ntype, "#64748B"))

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=[nid for nid in graph.nodes()],
        textposition="top center",
        hoverinfo="text",
        hovertext=node_text,
        marker=dict(
            size=28,
            color=node_colors,
            line_width=2,
            line_color="#1E293B",
        ),
    )

    fig_topo = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=20, r=20, t=20),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            height=340,
        ),
    )
    st.plotly_chart(fig_topo, use_container_width=True)


# Run simulation pipeline if button is pressed or if state exists
if run_button or "cascade_result" in st.session_state:
    if run_button or "cascade_result" not in st.session_state:
        with st.spinner("Executing Monte Carlo cascade simulation & agent recovery formulation..."):
            cascade = analyze_cascade(
                graph,
                disruption,
                runs=runs,
                sim_duration_days=sim_days,
                base_seed=int(random_seed),
            )
            orchestrator = AgentOrchestrator()
            plans = orchestrator.formulate_plans(graph, cascade)
            counterfactual_results = evaluate_counterfactual_plans(
                graph,
                plans,
                runs=runs,
                sim_duration_days=sim_days,
                base_seed=int(random_seed),
            )
            scorer = PlanScorer(weight_cost=0.35, weight_service_level=0.35, weight_co2=0.15, weight_resilience=0.15)
            scored_plans = scorer.score_plans(counterfactual_results)
            pareto_plans = get_pareto_plans(counterfactual_results)

            generator = ExecutiveBriefingGenerator()
            briefing_text = generator.generate_briefing(cascade, scored_plans, pareto_plans)

            st.session_state["cascade_result"] = cascade
            st.session_state["plans"] = plans
            st.session_state["scored_plans"] = scored_plans
            st.session_state["pareto_plans"] = pareto_plans
            st.session_state["briefing_text"] = briefing_text

    cascade = st.session_state["cascade_result"]
    scored_plans = st.session_state["scored_plans"]
    pareto_plans = st.session_state["pareto_plans"]
    briefing_text = st.session_state["briefing_text"]

    # Tab 2: Cascade Analysis
    with tab_cascade:
        st.subheader("Disruption Cascade Impact Assessment")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Baseline Service Level",
            f"{cascade.baseline_summary.mean_service_level * 100:.1f}%",
        )
        c2.metric(
            "Disrupted Service Level",
            f"{cascade.disrupted_summary.mean_service_level * 100:.1f}%",
            delta=f"{(cascade.disrupted_summary.mean_service_level - cascade.baseline_summary.mean_service_level) * 100:.1f}%",
            delta_color="inverse",
        )
        c3.metric(
            "Revenue at Risk",
            f"${cascade.revenue_at_risk:,.2f}",
        )
        c4.metric(
            "Cost Impact Delta",
            f"${cascade.cost_delta:+,.2f}",
        )

        st.markdown("---")
        col_cas_1, col_cas_2 = st.columns([1, 1])
        with col_cas_1:
            st.write("**Cascade Timeline & Stockout Failures**")
            st.info(
                f"**Earliest Failure Detected:** Node `{cascade.first_stockout_node or 'None'}` on Day **{cascade.first_stockout_day or 'N/A'}**\n\n"
                f"**Stockout Impact Propagation:** Node experienced zero-inventory stockouts leading to order backlogs downstream."
            )
            # Comparison Bar Chart
            df_comp = pd.DataFrame(
                {
                    "Metric": ["Service Level (%)", "Total Cost ($k)", "Stockout Days"],
                    "Baseline": [
                        cascade.baseline_summary.mean_service_level * 100,
                        cascade.baseline_summary.mean_total_cost / 1000,
                        cascade.baseline_summary.mean_stockout_days,
                    ],
                    "Disrupted": [
                        cascade.disrupted_summary.mean_service_level * 100,
                        cascade.disrupted_summary.mean_total_cost / 1000,
                        cascade.disrupted_summary.mean_stockout_days,
                    ],
                }
            )
            fig_bar = px.bar(
                df_comp,
                x="Metric",
                y=["Baseline", "Disrupted"],
                barmode="group",
                title="Baseline vs. Disrupted Scenario",
                color_discrete_sequence=["#10B981", "#EF4444"],
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_cas_2:
            st.write("**Disruption Shock Attributes**")
            st.json(cascade.disruption_event.to_dict())

    # Tab 3: Autonomous Recovery Plans
    with tab_recovery:
        st.subheader("Autonomous Multi-Agent Recovery Candidate Plans")
        st.write("Ranked by weighted multi-criteria score (Cost, Service Level, CO2, Resilience):")

        pareto_ids = {p.plan.id for p in pareto_plans}

        plan_summary_rows = []
        for sp in scored_plans:
            r = sp.raw_result
            plan_summary_rows.append(
                {
                    "Rank": f"#{sp.rank}",
                    "Plan Name": sp.plan_name,
                    "Score (0-100)": round(sp.final_score, 1),
                    "Post-Recovery Service": f"{r.post_recovery_service_level * 100:.1f}%",
                    "Total Effective Cost": f"${r.total_effective_cost:,.2f}",
                    "CO2 Emissions (kg)": f"{r.post_recovery_co2:,.1f}",
                    "Resilience Score": f"{r.resilience_score:.2f}",
                    "Actions": len(sp.raw_result.plan.actions),
                    "Pareto Optimal": "YES" if sp.plan_id in pareto_ids else "NO",
                }
            )
        st.dataframe(pd.DataFrame(plan_summary_rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.write("**Detailed Actions per Plan**")
        for sp in scored_plans:
            with st.expander(f"Plan #{sp.rank}: {sp.plan_name} — Score: {sp.final_score:.1f}"):
                act_rows = []
                for act in sp.raw_result.plan.actions:
                    act_rows.append(
                        {
                            "Action Type": act.action_type.capitalize(),
                            "Target": act.target_id,
                            "Proposed Quantity": act.quantity,
                            "Estimated Cost ($)": f"${act.estimated_cost:,.2f}",
                            "Parameters": str(act.parameters),
                        }
                    )
                st.dataframe(pd.DataFrame(act_rows), use_container_width=True, hide_index=True)

    # Tab 4: Pareto Frontier
    with tab_pareto:
        st.subheader("Multi-Objective Pareto Trade-Off Frontier")
        st.write("Visualizing the trade-off between **Total Effective Cost** vs. **Post-Recovery Service Level**:")

        pareto_scatter_data = []
        for sp in scored_plans:
            r = sp.raw_result
            is_pareto = sp.plan_id in pareto_ids
            pareto_scatter_data.append(
                {
                    "Plan": sp.plan_name,
                    "Total Cost ($)": r.total_effective_cost,
                    "Service Level (%)": r.post_recovery_service_level * 100,
                    "CO2 (kg)": r.post_recovery_co2,
                    "Pareto Frontier": "Pareto Optimal" if is_pareto else "Dominated",
                    "Score": sp.final_score,
                }
            )
        df_pareto = pd.DataFrame(pareto_scatter_data)

        fig_scatter = px.scatter(
            df_pareto,
            x="Total Cost ($)",
            y="Service Level (%)",
            color="Pareto Frontier",
            size="Score",
            hover_name="Plan",
            hover_data={"Total Cost ($)": ":$,.0f", "Service Level (%)": ":.1f%", "Score": ":.1f"},
            color_discrete_map={"Pareto Optimal": "#10B981", "Dominated": "#94A3B8"},
            title="Pareto Optimal Frontier (Service Level vs Cost)",
        )
        fig_scatter.update_traces(marker=dict(line=dict(width=1, color="DarkSlateGrey")))
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Tab 5: Executive Briefing
    with tab_briefing:
        st.subheader("Executive Incident Response Memo")
        st.markdown(briefing_text)
        st.download_button(
            label="Download Briefing (Markdown)",
            data=briefing_text,
            file_name="supply_chain_incident_briefing.md",
            mime="text/markdown",
        )
else:
    with tab_cascade:
        st.info("👈 Select your disruption scenario and click **'Run Simulation & Recovery'** in the sidebar to simulate cascade propagation.")
    with tab_recovery:
        st.info("👈 Click **'Run Simulation & Recovery'** to generate autonomous agent proposals.")
    with tab_pareto:
        st.info("👈 Run the simulation to view multi-objective Pareto trade-offs.")
    with tab_briefing:
        st.info("👈 Run the simulation to view the executive incident response memo.")
