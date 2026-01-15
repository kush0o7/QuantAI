from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.schemas.graph import (
    GraphEdgeCreate,
    GraphEdgeRead,
    GraphNodeCreate,
    GraphNodeRead,
)
from data.storage.db import get_session
from data.storage.repositories import graph_repo

router = APIRouter()


@router.post("/graph/nodes", response_model=GraphNodeRead)
def create_node(payload: GraphNodeCreate, session: Session = Depends(get_session)):
    node = graph_repo.create_node(
        session,
        company_id=payload.company_id,
        tenant_id=payload.tenant_id,
        node_type=payload.node_type,
        label=payload.label,
        details=payload.details,
    )
    return node


@router.get("/graph/nodes", response_model=list[GraphNodeRead])
def list_nodes(
    tenant_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
):
    return graph_repo.list_nodes(session, tenant_id=tenant_id)


@router.post("/graph/edges", response_model=GraphEdgeRead)
def create_edge(payload: GraphEdgeCreate, session: Session = Depends(get_session)):
    edge = graph_repo.create_edge(
        session,
        src_node_id=payload.src_node_id,
        dst_node_id=payload.dst_node_id,
        relation_type=payload.relation_type,
        weight=payload.weight,
        details=payload.details,
    )
    return edge


@router.get("/graph/edges", response_model=list[GraphEdgeRead])
def list_edges(session: Session = Depends(get_session)):
    return graph_repo.list_edges(session)
