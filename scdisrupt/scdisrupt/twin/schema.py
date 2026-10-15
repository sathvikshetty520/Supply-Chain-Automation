"""Pydantic validation schemas for digital twin network specification."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class InventoryPolicyConfig(BaseModel):
    initial_inventory: float = Field(..., ge=0.0)
    reorder_point: float = Field(..., ge=0.0)
    order_quantity: float = Field(..., gt=0.0)
    safety_stock: float = Field(..., ge=0.0)
    capacity: float = Field(..., gt=0.0)

    @model_validator(mode="after")
    def validate_policy_bounds(self):
        if self.safety_stock > self.reorder_point:
            # While mathematically possible in unusual policies, warn/check bounds
            pass
        if self.initial_inventory > self.capacity:
            raise ValueError("initial_inventory cannot exceed node capacity")
        return self


class DemandConfig(BaseModel):
    distribution: Literal["normal", "poisson", "lognormal"] = "normal"
    mean: float = Field(..., gt=0.0)
    std: float = Field(default=0.0, ge=0.0)


class SupplierConfig(BaseModel):
    id: str
    name: str
    location: str
    daily_capacity: float = Field(..., gt=0.0)
    unit_cost: float = Field(..., ge=0.0)
    reliability: float = Field(default=1.0, ge=0.0, le=1.0)


class FactoryConfig(BaseModel):
    id: str
    name: str
    location: str
    daily_capacity: float = Field(..., gt=0.0)
    holding_cost_per_day: float = Field(default=0.5, ge=0.0)
    inventory_policy: InventoryPolicyConfig


class WarehouseConfig(BaseModel):
    id: str
    name: str
    location: str
    holding_cost_per_day: float = Field(default=0.8, ge=0.0)
    stockout_penalty_per_day: float = Field(default=25.0, ge=0.0)
    inventory_policy: InventoryPolicyConfig


class CustomerConfig(BaseModel):
    id: str
    name: str
    location: str
    revenue_per_unit: float = Field(..., gt=0.0)
    demand: DemandConfig


class LaneConfig(BaseModel):
    id: str
    origin: str
    destination: str
    mode: Literal["ocean", "air", "rail", "road"] = "ocean"
    lead_time_mean: float = Field(..., gt=0.0)
    lead_time_std: float = Field(default=0.0, ge=0.0)
    cost_per_unit: float = Field(..., ge=0.0)
    capacity: float = Field(..., gt=0.0)
    co2_per_unit: float = Field(default=1.0, ge=0.0)


class NetworkConfig(BaseModel):
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    suppliers: List[SupplierConfig] = Field(default_factory=list)
    factories: List[FactoryConfig] = Field(default_factory=list)
    warehouses: List[WarehouseConfig] = Field(default_factory=list)
    customers: List[CustomerConfig] = Field(default_factory=list)
    lanes: List[LaneConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self):
        all_node_ids = {
            *[s.id for s in self.suppliers],
            *[f.id for f in self.factories],
            *[w.id for w in self.warehouses],
            *[c.id for c in self.customers],
        }

        # Check unique node IDs
        total_nodes = (
            len(self.suppliers)
            + len(self.factories)
            + len(self.warehouses)
            + len(self.customers)
        )
        if len(all_node_ids) != total_nodes:
            raise ValueError("Node IDs across all types must be strictly unique.")

        # Check lane endpoints exist
        for lane in self.lanes:
            if lane.origin not in all_node_ids:
                raise ValueError(f"Lane {lane.id} origin '{lane.origin}' does not exist.")
            if lane.destination not in all_node_ids:
                raise ValueError(f"Lane {lane.id} destination '{lane.destination}' does not exist.")
        return self
