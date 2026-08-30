import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    INVESTIGATOR = "investigator"
    VIEWER = "viewer"


class CaseStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class ArtifactStatus(str, enum.Enum):
    QUEUED = "queued"
    PARSING = "parsing"
    PARSED = "parsed"
    PARSE_FAILED = "parse_failed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid4:
    return uuid4()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.VIEWER,
    )
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    cases = relationship("Case", secondary="case_investigators", back_populates="investigators")


class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(CaseStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=CaseStatus.OPEN,
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    devices = relationship("Device", back_populates="case", cascade="all, delete-orphan")
    artifacts = relationship("RawArtifact", back_populates="case", cascade="all, delete-orphan")
    log_events = relationship("LogEvent", back_populates="case", cascade="all, delete-orphan")
    investigators = relationship("User", secondary="case_investigators", back_populates="cases")


class CaseInvestigator(Base):
    __tablename__ = "case_investigators"

    case_id = Column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    device_type = Column(String(50), nullable=False)  # pc, mobile, server, network
    os = Column(String(100), nullable=True)
    owner = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    case = relationship("Case", back_populates="devices")
    artifacts = relationship("RawArtifact", back_populates="device", cascade="all, delete-orphan")


class RawArtifact(Base):
    __tablename__ = "raw_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    filename = Column(String(500), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    storage_path = Column(String(1000), nullable=False)
    status = Column(
        Enum(ArtifactStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ArtifactStatus.QUEUED,
    )
    status_reason = Column(Text, nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    case = relationship("Case", back_populates="artifacts")
    device = relationship("Device", back_populates="artifacts")


class LogEvent(Base):
    __tablename__ = "log_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    artifact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("raw_artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    source_type = Column(
        String(100), nullable=False
    )  # windows_evtx, linux_syslog, android_logcat, etc.
    actor = Column(String(500), nullable=True)
    action = Column(String(255), nullable=False)
    object = Column(String(1000), nullable=True)
    ip_address = Column(String(45), nullable=True, index=True)
    file_hash = Column(String(64), nullable=True, index=True)
    detail = Column(Text, nullable=True)
    raw_line = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    case = relationship("Case", back_populates="log_events")
    device = relationship("Device")
    artifact = relationship("RawArtifact")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=False)
    target_id = Column(String(255), nullable=True)
    detail = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)


class Entity(Base):
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type = Column(String(50), nullable=False)  # user, device, file, ip, hash
    value = Column(String(1000), nullable=False)
    entity_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    case = relationship("Case")
    outgoing_edges = relationship(
        "CorrelationEdge",
        foreign_keys="CorrelationEdge.entity_a_id",
        back_populates="entity_a",
    )
    incoming_edges = relationship(
        "CorrelationEdge",
        foreign_keys="CorrelationEdge.entity_b_id",
        back_populates="entity_b",
    )


class CorrelationEdge(Base):
    __tablename__ = "correlation_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_a_id = Column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_b_id = Column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type = Column(
        String(100), nullable=False
    )  # same_file, usb_transfer, bluetooth_send, email_attach, etc.
    confidence = Column(Float, nullable=False, default=0.0)
    evidence_event_ids = Column(JSON, nullable=True)  # list of LogEvent IDs that support this edge
    explanation_json = Column(JSON, nullable=True)  # SHAP/feature attribution explanation
    model_version = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    case = relationship("Case")
    entity_a = relationship("Entity", foreign_keys=[entity_a_id], back_populates="outgoing_edges")
    entity_b = relationship("Entity", foreign_keys=[entity_b_id], back_populates="incoming_edges")


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_ids = Column(JSON, nullable=True)  # list of LogEvent IDs involved
    score = Column(Float, nullable=False)  # anomaly score (higher = more anomalous)
    severity = Column(String(20), nullable=False, default="low")  # low, medium, high, critical
    category = Column(
        String(100), nullable=False
    )  # off_hours, volume_spike, suspicious_process, ransomware, etc.
    model_name = Column(String(100), nullable=False)  # isolation_forest, ransomware_detector, etc.
    model_version = Column(String(100), nullable=True)
    explanation_json = Column(JSON, nullable=True)  # SHAP feature attribution
    reviewed_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_status = Column(
        String(50), nullable=False, default="pending"
    )  # pending, confirmed, dismissed
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    case = relationship("Case")
    reviewer = relationship("User")


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format = Column(String(20), nullable=False)  # pdf, csv, json
    status = Column(
        Enum(ReportStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ReportStatus.DRAFT,
    )
    title = Column(String(500), nullable=False)
    content_hash = Column(String(64), nullable=False)
    content_json = Column(JSON, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    case = relationship("Case")
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
