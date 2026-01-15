from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class GraphNodeCreate(BaseModel):
    company_id: int | None = None
    tenant_id: int | None = None
    node_type: str
    label: str
    details: dict | None = None


class GraphNodeRead(BaseModel):
    id: int
    company_id: int | None
    tenant_id: int | None
    node_type: str
    label: str
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class GraphEdgeCreate(BaseModel):
    src_node_id: int
    dst_node_id: int
    relation_type: str
    weight: float = 0.0
    details: dict | None = None


class GraphEdgeRead(BaseModel):
    id: int
    src_node_id: int
    dst_node_id: int
    relation_type: str
    weight: float
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}
