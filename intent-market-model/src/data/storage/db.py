from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from core.config import get_settings
from core.types import EmbeddingType, JSONDict
from core.utils.time import utc_now

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

    companies = relationship("Company", back_populates="tenant")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

    signals = relationship("SignalEvent", back_populates="company")
    intents = relationship("IntentHypothesis", back_populates="company")
    tenant = relationship("Tenant", back_populates="companies")


class SignalEvent(Base):
    __tablename__ = "signal_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text_uri: Mapped[str | None] = mapped_column(Text)
    structured_fields: Mapped[dict] = mapped_column(JSONDict(), default=dict)
    diff: Mapped[dict] = mapped_column(JSONDict(), default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        EmbeddingType(get_settings().embedding_dim)
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

    company = relationship("Company", back_populates="signals")


class IntentHypothesis(Base):
    __tablename__ = "intent_hypotheses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    intent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[list[dict]] = mapped_column(JSONDict(), default=list)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

    company = relationship("Company", back_populates="intents")


class OutcomeEvent(Base):
    __tablename__ = "outcome_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    outcome_type: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(JSONDict(), default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IntentGraphNode(Base):
    __tablename__ = "intent_graph_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.id"))
    node_type: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict] = mapped_column(JSONDict(), default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IntentGraphEdge(Base):
    __tablename__ = "intent_graph_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    src_node_id: Mapped[int] = mapped_column(ForeignKey("intent_graph_nodes.id"), nullable=False)
    dst_node_id: Mapped[int] = mapped_column(ForeignKey("intent_graph_nodes.id"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    details: Mapped[dict] = mapped_column(JSONDict(), default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IntentBacktestResult(Base):
    __tablename__ = "intent_backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    outcome_id: Mapped[int | None] = mapped_column(Integer)
    outcome_type: Mapped[str] = mapped_column(String(100), nullable=False)
    intent_id: Mapped[int | None] = mapped_column(Integer)
    intent_type: Mapped[str | None] = mapped_column(String(100))
    outcome_timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    intent_timestamp: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    lag_days: Mapped[float | None] = mapped_column(Float)
    matched: Mapped[bool] = mapped_column(Boolean, default=False)
    run_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    if engine.dialect.name != "postgresql":
        Base.metadata.create_all(bind=engine)
        return

    migrations_path = Path(__file__).parent / "migrations.sql"
    if migrations_path.exists():
        sql = migrations_path.read_text(encoding="utf-8")
        with engine.begin() as connection:
            for statement in [s.strip() for s in sql.split(";") if s.strip()]:
                connection.exec_driver_sql(statement)
    else:
        Base.metadata.create_all(bind=engine)


def ensure_company_exists(company_id: int) -> None:
    with SessionLocal() as session:
        exists = session.execute(select(Company.id).where(Company.id == company_id)).first()
        if not exists:
            raise ValueError(f"Company {company_id} not found")
