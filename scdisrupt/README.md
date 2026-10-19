# SC-Disrupt: Autonomous Supply-Chain Disruption Simulator & Digital Twin

[![CI](https://github.com/sathvikshetty520/Supply-Chain-Automation/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/sathvikshetty520/Supply-Chain-Automation)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An agentic discrete-event simulation engine and digital twin platform for stress-testing global supply chains against high-impact disruptions, generating multi-objective autonomous recovery plans, evaluating Pareto trade-offs, and compiling C-suite executive briefings.

---

## Key Features

1. **Digital Twin Topology Modeling (`scdisrupt.twin`)**
   - YAML-configured multi-echelon network topology: Tier-1/2 Suppliers, Seaports, Distribution Centers, and Retail Hubs.
   - NetworkX-based graph representations with stochastic lead times, capacity limits, and CO₂ emission factors.

2. **Discrete-Event Simulation Engine (`scdisrupt.simulation`)**
   - Built on SimPy with Monte Carlo parameter perturbation across orders, transport delays, and production constraints.
   - Comprehensive performance metrics: Fill rate, Mean Service Level, Stockout Days, Total Landed Cost, and Lost Revenue.

3. **Disruption Catalog & Cascade Modeling (`scdisrupt.disruptions`)**
   - Injectable shock events: Port Strikes, Supplier Facility Failures, Sudden Demand Surges, and Currency/Tariff Shocks.
   - Cascade analysis computing time-to-first-stockout, bottleneck propagation, and revenue-at-risk.

4. **Multi-Agent Autonomous Recovery (`scdisrupt.agents` & `scdisrupt.optimizer`)**
   - Specialized agent roles:
     - **Procurement Agent**: Identifies alternative suppliers, spot purchasing, and expedite contracts.
     - **Logistics Agent**: Reroutes freight via air/rail, adjusts batch sizes, and shifts transport corridors.
     - **Finance Agent**: Sets working capital and budget caps, enforcing cost constraints.
   - PuLP / Linear Programming optimization for cost-minimized lane allocations.

5. **Counterfactual Evaluation & Pareto Frontier (`scdisrupt.scoring`)**
   - Multi-criteria weighted utility scoring balancing Cost, Service Level, CO₂ Footprint, and Resilience.
   - Non-dominated Pareto frontier extraction for transparent executive decision-making.

6. **GenAI Explanation Engine (`scdisrupt.explain`)**
   - Automated root-cause diagnostics and incident response memos formatted for executive leadership.

7. **FastAPI REST API & Interactive UI (`scdisrupt.api` & `scdisrupt.ui`)**
   - Production REST endpoints for headless integration and pipeline orchestration.
   - Streamlit dashboard providing network visualizers, simulation triggers, and Pareto plots.

---

## Repository Structure

```
Supply-Chain-Automation/
└── scdisrupt/
    ├── configs/
    │   └── sample_network.yaml         # Supply chain digital twin network definition
    ├── scdisrupt/
    │   ├── twin/                       # Schema, config loaders, graph builder
    │   ├── simulation/                 # SimPy discrete-event simulation & Monte Carlo
    │   ├── disruptions/                # Disruption catalog & cascade impact analysis
    │   ├── agents/                     # Procurement, Logistics, Finance orchestrators
    │   ├── optimizer/                  # LP / PuLP allocation solver
    │   ├── scoring/                    # Counterfactual evaluator, Pareto frontier
    │   ├── explain/                    # GenAI explanation & executive briefing memos
    │   └── api/                        # FastAPI REST service & schema models
    ├── scripts/
    │   └── run_demo.py                 # End-to-end command-line simulation demo
    ├── ui/
    │   └── app.py                      # Interactive Streamlit dashboard
    ├── tests/                          # 22-test automated unit and integration suite
    └── pyproject.toml                  # Package configuration & dependencies
```

---

## Installation & Setup

### Prerequisites
- Python >= 3.11

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/sathvikshetty520/Supply-Chain-Automation.git
cd Supply-Chain-Automation/scdisrupt

# Install package and dependencies
pip install -e .
```

### 2. Run Test Suite
```bash
python -m pytest
```

---

## Quickstart & Usage

### Option 1: Interactive Streamlit Dashboard
Launch the web interface for visual topology inspection and real-time disruption simulation:
```bash
streamlit run ui/app.py
```
Open your browser at `http://localhost:8501`.

### Option 2: Command-Line Demo Pipeline
Run an automated end-to-end Monte Carlo simulation with agent recovery and Pareto ranking:
```bash
# Port Strike Scenario
python scripts/run_demo.py --disruption port_strike --runs 5 --days 45

# Supplier Failure Scenario
python scripts/run_demo.py --disruption supplier_failure --runs 5 --days 45
```

### Option 3: FastAPI REST Service
Start the headless REST API service:
```bash
uvicorn scdisrupt.api.app:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### Example REST Endpoints:
- `GET /health` - Health check status
- `GET /network` - Digital twin nodes and transport lanes
- `POST /simulate` - Run Monte Carlo baseline or disrupted simulation
- `POST /cascade` - Analyze disruption cascade impact and stockout propagation
- `POST /recover` - Formulate and evaluate multi-agent recovery plans with Pareto rankings

---

## License

This project is licensed under the MIT License.
