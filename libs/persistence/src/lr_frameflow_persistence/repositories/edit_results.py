from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lr_frameflow_persistence.models import EditResult


class EditResultRepository:
    @staticmethod
    def get_by_job_id(session: Session, job_id: uuid.UUID) -> EditResult | None:
        stmt = select(EditResult).where(EditResult.job_id == job_id)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_all_by_job_id(session: Session, job_id: uuid.UUID) -> list[EditResult]:
        stmt = select(EditResult).where(EditResult.job_id == job_id)
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def create(
        session: Session,
        *,
        result_id: uuid.UUID,
        job_id: uuid.UUID,
        photo_id: uuid.UUID,
        profile_id: uuid.UUID,
        lr_settings: dict[str, Any],
        s3_key: str | None = None,
    ) -> EditResult:
        result = EditResult(
            id=result_id,
            job_id=job_id,
            photo_id=photo_id,
            profile_id=profile_id,
            lr_settings=lr_settings,
            s3_key=s3_key,
        )
        session.add(result)
        session.flush()
        return result
