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
    UniqueConstraint,
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
    greenhouse_board: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

    signals = relationship("SignalEvent", back_populates="company")
    intents = relationship("IntentHypothesis", back_populates="company")
    tenant = relationship("Tenant", back_populates="companies")


class SignalEvent(Base):
    __tablename__ = "signal_events"
    __table_args__ = (
        UniqueConstraint("company_id", "event_hash", name="idx_signal_events_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text_uri: Mapped[str | None] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text)
    structured_fields: Mapped[dict] = mapped_column(JSONDict(), default=dict)
    diff: Mapped[dict] = mapped_column(JSONDict(), default=dict)
    vectorizer_version: Mapped[str | None] = mapped_column(String(50))
    tokens: Mapped[list[str]] = mapped_column(JSONDict(), default=list)
    drift_score: Mapped[float | None] = mapped_column(Float)
    top_terms_delta: Mapped[list[dict]] = mapped_column(JSONDict(), default=list)
    role_bucket_delta: Mapped[dict] = mapped_column(JSONDict(), default=dict)
    tech_tag_delta: Mapped[dict] = mapped_column(JSONDict(), default=dict)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
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
    readiness_score: Mapped[float | None] = mapped_column(Float)
    alert_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_reason: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[list[dict]] = mapped_column(JSONDict(), default=list)
    rule_hits_json: Mapped[list[dict]] = mapped_column(JSONDict(), default=list)
    explanations_json: Mapped[list[dict]] = mapped_column(JSONDict(), default=list)
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


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, default=60)
    last_used_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RateLimit(Base):
    __tablename__ = "rate_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), nullable=False)
    window_start: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0)


class ResponseCache(Base):
    __tablename__ = "response_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONDict(), default=dict)
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_key_id: Mapped[int | None] = mapped_column(ForeignKey("api_keys.id"))
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.id"))
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
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
