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
    CyberattackDisruption,
    CanalBlockageDisruption,
    RawMaterialExportBanDisruption,
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
    options=[
        "Port Strike",
        "Supplier Failure",
        "Demand Surge",
        "Currency Shock",
        "Cyberattack / Ransomware",
        "Canal Blockage",
        "Raw Material Export Embargo",
    ],
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
elif disruption_type == "Currency Shock":
    cost_m = st.sidebar.slider("Cost Multiplier", 1.1, 2.5, 1.25, 0.05)
    disruption = CurrencyShockDisruption(cost_multiplier=cost_m)
elif disruption_type == "Cyberattack / Ransomware":
    targetable = [n for n, d in graph.nodes(data=True) if d.get("type") in ["factory", "warehouse"]]
    sel_node = st.sidebar.selectbox("Target Facility", options=targetable if targetable else ["FAC_1"])
    tp_red = st.sidebar.slider("Throughput Reduction", 0.3, 1.0, 0.85, 0.05)
    disruption = CyberattackDisruption(target_node_id=sel_node, throughput_reduction=tp_red)
elif disruption_type == "Canal Blockage":
    c_lt = st.sidebar.slider("Canal Lead Time Multiplier", 2.0, 8.0, 4.0, 0.5)
    c_cost = st.sidebar.slider("Fuel Surcharge Multiplier", 1.2, 2.5, 1.6, 0.1)
    disruption = CanalBlockageDisruption(lead_time_multiplier=c_lt, cost_multiplier=c_cost)
else:
    supp_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "supplier"]
    sel_suppliers = st.sidebar.multiselect("Embargoed Suppliers", options=supp_nodes, default=supp_nodes[:1])
    curtail = st.sidebar.slider("Export Curtailment", 0.2, 1.0, 0.90, 0.05)
    tariff = st.sidebar.slider("Spot Tariff Surcharge", 1.1, 3.0, 1.75, 0.05)
    disruption = RawMaterialExportBanDisruption(
        supplier_ids=sel_suppliers if sel_suppliers else ["SUP_1"],
        capacity_curtailment=curtail,
        tariff_surcharge=tariff,
    )

st.sidebar.markdown("---")
st.sidebar.subheader("Simulation Parameters")
runs = st.sidebar.slider("Monte Carlo Runs", 1, 20, 5, 1)
sim_days = st.sidebar.slider("Horizon (Days)", 15, 90, 45, 5)
random_seed = st.sidebar.number_input("Random Seed", value=42, step=1)

with st.sidebar.expander("⚖️ Multi-Criteria Scorer Weights", expanded=False):
    st.caption("Adjust policy weights for candidate ranking (auto-normalized):")
    w_cost = st.slider("Cost Weight", 0.0, 1.0, 0.35, 0.05)
    w_sl = st.slider("Service Level Weight", 0.0, 1.0, 0.35, 0.05)
    w_co2 = st.slider("Carbon / CO2 Weight", 0.0, 1.0, 0.15, 0.05)
    w_resil = st.slider("Resilience Weight", 0.0, 1.0, 0.15, 0.05)

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
        st.metric("Suppliers", len(config.suppliers))
    with col_t4:
        st.metric("Demand Centers", len(config.customers))

    # Network Node Table
    node_rows = []
    for nid, d in graph.nodes(data=True):
        inv = d.get("inventory_policy")
        node_rows.append(
            {
                "Node ID": str(nid),
                "Name": str(d.get("name", nid)),
                "Type": str(d.get("type", "unknown")).capitalize(),
                "Location": str(d.get("location", "")),
                "Initial Inventory": str(inv.initial_inventory) if inv and inv.initial_inventory is not None else "-",
                "Safety Stock": str(inv.safety_stock) if inv and inv.safety_stock is not None else "-",
                "Max Capacity": str(inv.capacity if inv and inv.capacity is not None else d.get("daily_capacity", "-")),
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

    # Filters for tables
    f_col1, f_col2 = st.columns([1, 1])
    with f_col1:
        types_avail = sorted(list(df_nodes["Type"].unique()))
        selected_types = st.multiselect("Filter Nodes by Type", options=types_avail, default=types_avail)
    with f_col2:
        modes_avail = sorted(list(df_lanes["Transport Mode"].unique()))
        selected_modes = st.multiselect("Filter Lanes by Mode", options=modes_avail, default=modes_avail)

    df_nodes_filtered = df_nodes[df_nodes["Type"].isin(selected_types)] if selected_types else df_nodes
    df_lanes_filtered = df_lanes[df_lanes["Transport Mode"].isin(selected_modes)] if selected_modes else df_lanes

    c_left, c_right = st.columns([1, 1])
    with c_left:
        st.write(f"**Nodes & Facilities ({len(df_nodes_filtered)}/{len(df_nodes)})**")
        st.dataframe(df_nodes_filtered, use_container_width=True, hide_index=True)
    with c_right:
        st.write(f"**Transportation Lanes & Lead Times ({len(df_lanes_filtered)}/{len(df_lanes)})**")
        st.dataframe(df_lanes_filtered, use_container_width=True, hide_index=True)

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
            scorer = PlanScorer(
                weight_cost=w_cost,
                weight_service_level=w_sl,
                weight_co2=w_co2,
                weight_resilience=w_resil,
            )
            scored_plans = scorer.score_plans(counterfactual_results)
            pareto_plans = get_pareto_plans(counterfactual_results)

            generator = ExecutiveBriefingGenerator()
            briefing_text = generator.generate_briefing(cascade, scored_plans, pareto_plans)

            st.session_state["cascade_result"] = cascade
            st.session_state["counterfactual_results"] = counterfactual_results
            st.session_state["plans"] = plans
            st.session_state["scored_plans"] = scored_plans
            st.session_state["pareto_plans"] = pareto_plans
            st.session_state["briefing_text"] = briefing_text

    # Re-score if weights changed dynamically without re-running full simulation
    if "counterfactual_results" in st.session_state:
        scorer = PlanScorer(
            weight_cost=w_cost,
            weight_service_level=w_sl,
            weight_co2=w_co2,
            weight_resilience=w_resil,
        )
        scored_plans = scorer.score_plans(st.session_state["counterfactual_results"])
        st.session_state["scored_plans"] = scored_plans

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
                    "Metric": ["Service Level (%)", "Mean Cost ($k)", "Mean CO2 (t)"],
                    "Baseline": [
                        cascade.baseline_summary.mean_service_level * 100,
                        cascade.baseline_summary.mean_cost / 1000,
                        cascade.baseline_summary.mean_co2 / 1000,
                    ],
                    "Disrupted": [
                        cascade.disrupted_summary.mean_service_level * 100,
                        cascade.disrupted_summary.mean_cost / 1000,
                        cascade.disrupted_summary.mean_co2 / 1000,
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
            st.write("**Vulnerable Facilities by Stockout Probability**")
            if cascade.vulnerable_nodes_ranked:
                df_vuln = pd.DataFrame(cascade.vulnerable_nodes_ranked)
                df_vuln_display = df_vuln.rename(
                    columns={
                        "node_id": "Node ID",
                        "node_name": "Facility Name",
                        "disrupted_prob": "Disrupted Stockout Prob",
                        "baseline_prob": "Baseline Stockout Prob",
                        "delta_prob": "Risk Delta",
                    }
                )
                fig_vuln = px.bar(
                    df_vuln_display,
                    x="Disrupted Stockout Prob",
                    y="Facility Name",
                    orientation="h",
                    color="Risk Delta",
                    color_continuous_scale="Reds",
                    title="Facility Stockout Risk (Disrupted)",
                )
                fig_vuln.update_layout(yaxis=dict(autorange="reversed"), height=300)
                st.plotly_chart(fig_vuln, use_container_width=True)
            else:
                st.info("No vulnerable facility data recorded.")

        # Stockout propagation timeline chart
        if cascade.stockout_timeline:
            st.markdown("---")
            st.write("**Disruption Stockout Propagation Sequence**")
            tl_data = [
                {
                    "Day": evt.day,
                    "Node ID": evt.node_id,
                    "Facility": evt.node_name,
                    "Unmet Demand": evt.unmet_demand,
                    "Backorders": evt.backorders,
                }
                for evt in cascade.stockout_timeline
            ]
            df_tl = pd.DataFrame(tl_data)
            fig_tl = px.scatter(
                df_tl,
                x="Day",
                y="Facility",
                size="Backorders" if df_tl["Backorders"].sum() > 0 else "Unmet Demand",
                color="Facility",
                hover_data=["Day", "Node ID", "Unmet Demand", "Backorders"],
                title="Stockout Failure Propagation Over Time",
            )
            fig_tl.update_traces(marker=dict(symbol="diamond", line=dict(width=1, color="black")))
            st.plotly_chart(fig_tl, use_container_width=True)

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
                    act_type_val = act.action_type.value if hasattr(act.action_type, "value") else str(act.action_type)
                    act_rows.append(
                        {
                            "Agent": act.agent.capitalize(),
                            "Action Type": act_type_val.replace("_", " ").title(),
                            "Target Node/Lane": act.target_id,
                            "Estimated Cost ($)": f"${act.estimated_cost:,.2f}",
                            "Description": act.description or "-",
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

        col_p1, col_p2 = st.columns([1, 1])
        with col_p1:
            fig_scatter = px.scatter(
                df_pareto,
                x="Total Cost ($)",
                y="Service Level (%)",
                color="Pareto Frontier",
                size="Score",
                hover_name="Plan",
                hover_data={"Total Cost ($)": ":$,.0f", "Service Level (%)": ":.1f%", "Score": ":.1f"},
                color_discrete_map={"Pareto Optimal": "#10B981", "Dominated": "#94A3B8"},
                title="Pareto Frontier: Cost vs. Service Level",
            )
            fig_scatter.update_traces(marker=dict(line=dict(width=1, color="DarkSlateGrey")))
            st.plotly_chart(fig_scatter, use_container_width=True)

        with col_p2:
            st.write("**Multi-Dimensional Policy Comparison (Radar Profile)**")
            categories = ["Cost Efficiency", "Service Level", "CO2 Conservation", "Resilience"]
            fig_radar = go.Figure()
            colors = ["#3B82F6", "#10B981", "#F59E0B", "#EC4899"]

            for idx, sp in enumerate(scored_plans):
                r_vals = [
                    sp.normalized_cost_score * 100,
                    sp.normalized_service_score * 100,
                    sp.normalized_co2_score * 100,
                    sp.normalized_resilience_score * 100,
                ]
                # Close the radar loop
                r_vals.append(r_vals[0])
                cat_closed = categories + [categories[0]]
                fig_radar.add_trace(
                    go.Scatterpolar(
                        r=r_vals,
                        theta=cat_closed,
                        fill="toself",
                        name=f"#{sp.rank}: {sp.plan_name}",
                        line_color=colors[idx % len(colors)],
                        opacity=0.65,
                    )
                )

            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100]),
                ),
                showlegend=True,
                title="Normalized Performance Criteria (0-100)",
                height=380,
                margin=dict(t=40, b=30, l=40, r=40),
            )
            st.plotly_chart(fig_radar, use_container_width=True)

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
