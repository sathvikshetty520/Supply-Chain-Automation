"""Metrics collection and aggregation for SimPy simulation runs."""
from typing import Dict, List, Optional
import numpy as np

from scdisrupt.common.types import DailyMetrics, NodeDailyMetrics, RunMetrics


class SimulationMetricsCollector:
    """Collects and computes operational and financial metrics during a simulation run."""

    def __init__(self, seed: int):
        self.seed = seed
        self.daily_records: List[DailyMetrics] = []
        self.stockout_days: Dict[str, List[int]] = {}
        self.total_cost: float = 0.0
        self.total_revenue: float = 0.0
        self.total_co2: float = 0.0
        self.total_demand_volume: float = 0.0
        self.total_fulfilled_volume: float = 0.0
        self.total_orders_placed: int = 0
        self.total_orders_on_time: int = 0
        self.first_stockout_day: Optional[int] = None

    def record_day(
        self,
        day: int,
        node_records: Dict[str, NodeDailyMetrics],
        daily_transport_cost: float,
        daily_co2: float,
        daily_revenue: float,
        orders_placed: int = 0,
        orders_delivered: int = 0,
        orders_on_time: int = 0,
    ) -> DailyMetrics:
        """Record aggregate daily status and evaluate stockouts."""
        total_inv = sum(nr.inventory_level for nr in node_records.values())
        total_backorders = sum(nr.backorders for nr in node_records.values())
        holding_costs = sum(nr.holding_cost for nr in node_records.values())
        penalty_costs = sum(nr.stockout_penalty for nr in node_records.values())

        stockouts_today = 0
        for node_id, nr in node_records.items():
            if nr.unmet_demand > 0 or (nr.inventory_level <= 0 and nr.backorders > 0):
                stockouts_today += 1
                if node_id not in self.stockout_days:
                    self.stockout_days[node_id] = []
                self.stockout_days[node_id].append(day)
                if self.first_stockout_day is None:
                    self.first_stockout_day = day

        daily_total_cost = holding_costs + penalty_costs + daily_transport_cost
        self.total_cost += daily_total_cost
        self.total_revenue += daily_revenue
        self.total_co2 += daily_co2
        self.total_orders_placed += orders_placed
        self.total_orders_on_time += orders_on_time

        for nr in node_records.values():
            self.total_demand_volume += (nr.fulfilled_demand + nr.unmet_demand)
            self.total_fulfilled_volume += nr.fulfilled_demand

        metrics = DailyMetrics(
            day=day,
            total_inventory=total_inv,
            total_backorders=total_backorders,
            total_stockout_events=stockouts_today,
            orders_placed=orders_placed,
            orders_delivered=orders_delivered,
            orders_on_time=orders_on_time,
            daily_cost=daily_total_cost,
            daily_co2=daily_co2,
            revenue=daily_revenue,
            node_metrics=node_records,
        )
        self.daily_records.append(metrics)
        return metrics

    def compute_run_summary(self) -> RunMetrics:
        """Produce the final RunMetrics structure for this simulation run."""
        stockout_nodes = list(self.stockout_days.keys())
        stockout_duration = {k: len(v) for k, v in self.stockout_days.items()}
        
        # Service level: proportion of demand fulfilled on time / without stockout
        if self.total_demand_volume > 0:
            service_level = max(0.0, min(1.0, self.total_fulfilled_volume / self.total_demand_volume))
        else:
            service_level = 1.0

        return RunMetrics(
            seed=self.seed,
            total_cost=float(np.round(self.total_cost, 2)),
            total_revenue=float(np.round(self.total_revenue, 2)),
            total_profit=float(np.round(self.total_revenue - self.total_cost, 2)),
            total_co2=float(np.round(self.total_co2, 2)),
            service_level=float(np.round(service_level, 4)),
            stockout_occurred=len(stockout_nodes) > 0,
            stockout_nodes=stockout_nodes,
            first_stockout_day=self.first_stockout_day,
            stockout_duration_days=stockout_duration,
            daily_records=self.daily_records,
        )
