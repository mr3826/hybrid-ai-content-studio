import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from app.models.base import Base


class EvidenceSource(Base):
    """External or benchmark citation source with provenance metadata."""

    __tablename__ = "evidence_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    packet_id = Column(String(36), ForeignKey("research_packets.id", ondelete="SET NULL"), nullable=True, index=True)
    url = Column(String(1024), nullable=False)
    title = Column(String(512), nullable=False)
    domain = Column(String(255), nullable=False, index=True)
    source_type = Column(String(50), nullable=False, default="primary")  # primary, supporting, experiment
    trust_weight = Column(Float, nullable=False, default=1.0)
    author = Column(String(255), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    raw_content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    evidence_links = relationship("ClaimEvidence", back_populates="source", cascade="all, delete-orphan")


class Claim(Base):
    """Individual assertion with explicit provenance categorization."""

    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    packet_id = Column(String(36), ForeignKey("research_packets.id", ondelete="SET NULL"), nullable=True, index=True)
    text = Column(Text, nullable=False)
    claim_type = Column(
        String(50),
        nullable=False,
        default="external_fact",
        index=True,
    )  # external_fact, original_measurement, derived_conclusion, opinion, prediction_speculation
    confidence = Column(Float, nullable=False, default=1.0)
    is_verified = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    evidence_links = relationship("ClaimEvidence", back_populates="claim", cascade="all, delete-orphan")
    content_claims = relationship("ContentClaim", back_populates="claim", cascade="all, delete-orphan")
    conclusions = relationship("Conclusion", back_populates="claim")


class ClaimEvidence(Base):
    """Join entity linking claims to citations with precise quotes and confidence."""

    __tablename__ = "claim_evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(36), ForeignKey("evidence_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    quote = Column(Text, nullable=False)
    page_or_timestamp = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=False, default=0.9)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    claim = relationship("Claim", back_populates="evidence_links")
    source = relationship("EvidenceSource", back_populates="evidence_links")


class Experiment(Base):
    """Original studio test, lab benchmark, or workflow execution record."""

    __tablename__ = "experiments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    opportunity_id = Column(String(36), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    hypothesis = Column(Text, nullable=False)
    method = Column(Text, nullable=False)
    tools_models = Column(JSON, nullable=False, default=list)
    parameters = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    runs = relationship("ExperimentRun", back_populates="experiment", cascade="all, delete-orphan")
    conclusions = relationship("Conclusion", back_populates="experiment", cascade="all, delete-orphan")


class ExperimentRun(Base):
    """Single execution iteration of an experiment measuring latency, throughput, or cost."""

    __tablename__ = "experiment_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    run_number = Column(Integer, nullable=False, default=1)
    execution_time_ms = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="success")  # success, failed
    error_message = Column(Text, nullable=True)
    artifacts = Column(JSON, nullable=False, default=list)  # file paths, screenshots, output logs
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    experiment = relationship("Experiment", back_populates="runs")
    measurements = relationship("Measurement", back_populates="run", cascade="all, delete-orphan")


class Measurement(Base):
    """Quantitative empirical metric collected during an experiment run."""

    __tablename__ = "measurements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("experiment_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    metric = Column(String(255), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    context = Column(Text, nullable=True)
    sample_size = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    run = relationship("ExperimentRun", back_populates="measurements")


class Conclusion(Base):
    """Derived empirical finding synthesizing one or more experiment measurements."""

    __tablename__ = "conclusions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="SET NULL"), nullable=True, index=True)
    confidence = Column(Float, nullable=False, default=0.95)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    experiment = relationship("Experiment", back_populates="conclusions")
    claim = relationship("Claim", back_populates="conclusions")


class ContentClaim(Base):
    """Mapping of an empirical claim to a specific script section or scene."""

    __tablename__ = "content_claims"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    content_id = Column(String(36), nullable=False, index=True)  # project_id or script_id
    section_id = Column(String(100), nullable=False, default="evidence")  # hook, problem, test, evidence, result, cta
    quote_in_script = Column(Text, nullable=False)
    verification_status = Column(
        String(50),
        nullable=False,
        default="unsupported",
        index=True,
    )  # verified, unsupported, labeled_opinion, overridden
    is_overridden = Column(Boolean, nullable=False, default=False)
    override_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    claim = relationship("Claim", back_populates="content_claims")
