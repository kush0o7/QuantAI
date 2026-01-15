from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.storage.db import IntentGraphEdge, IntentGraphNode


def create_node(
    session: Session,
    company_id: int | None,
    tenant_id: int | None,
    node_type: str,
    label: str,
    details: dict | None = None,
) -> IntentGraphNode:
    node = IntentGraphNode(
        company_id=company_id,
        tenant_id=tenant_id,
        node_type=node_type,
        label=label,
        details=details or {},
    )
    session.add(node)
    session.commit()
    session.refresh(node)
    return node


def create_edge(
    session: Session,
    src_node_id: int,
    dst_node_id: int,
    relation_type: str,
    weight: float = 0.0,
    details: dict | None = None,
) -> IntentGraphEdge:
    edge = IntentGraphEdge(
        src_node_id=src_node_id,
        dst_node_id=dst_node_id,
        relation_type=relation_type,
        weight=weight,
        details=details or {},
    )
    session.add(edge)
    session.commit()
    session.refresh(edge)
    return edge


def list_nodes(session: Session, tenant_id: int | None = None, limit: int = 100) -> list[IntentGraphNode]:
    query = select(IntentGraphNode)
    if tenant_id is not None:
        query = query.where(IntentGraphNode.tenant_id == tenant_id)
    return list(session.execute(query.limit(limit)).scalars())


def list_edges(session: Session, limit: int = 100) -> list[IntentGraphEdge]:
    return list(session.execute(select(IntentGraphEdge).limit(limit)).scalars())
