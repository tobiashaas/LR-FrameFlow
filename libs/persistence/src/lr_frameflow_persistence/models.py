from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from lr_frameflow_domain.jobs import JobKind, JobStatus


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    payload_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)

    correlation_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(256), nullable=True)

    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    failure_reason: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def sync_kind_enum(self, kind: JobKind) -> None:
        self.kind = kind.value

    def sync_status_enum(self, status: JobStatus) -> None:
        self.status = status.value
