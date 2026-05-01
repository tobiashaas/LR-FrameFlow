from __future__ import annotations

import uuid
from typing import Any

from lr_frameflow_domain import JobKind, JobStatus
from lr_frameflow_persistence.models import Job
from sqlalchemy import select
from sqlalchemy.orm import Session


class JobRepository:
    @staticmethod
    def get_by_id(session: Session, job_id: uuid.UUID) -> Job | None:
        return session.get(Job, job_id)

    @staticmethod
    def get_by_idempotency_key(session: Session, key: str) -> Job | None:
        stmt = select(Job).where(Job.idempotency_key == key)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create(
        session: Session,
        *,
        job_id: uuid.UUID,
        kind: JobKind,
        payload_schema_version: str,
        payload: dict[str, Any],
        correlation_id: str | None,
        idempotency_key: str | None,
    ) -> Job:
        job = Job(
            id=job_id,
            kind=kind.value,
            status=JobStatus.QUEUED.value,
            payload_schema_version=payload_schema_version,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            payload=payload,
        )
        session.add(job)
        session.flush()
        return job

    @staticmethod
    def set_status(
        session: Session,
        job_id: uuid.UUID,
        status: JobStatus,
        *,
        failure_reason: str | None = None,
    ) -> Job | None:
        job = session.get(Job, job_id)
        if job is None:
            return None
        job.sync_status_enum(status)
        job.failure_reason = failure_reason
        session.flush()
        return job
