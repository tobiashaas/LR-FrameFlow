from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lr_frameflow_persistence.models import FeatureVector


class FeatureVectorRepository:
    @staticmethod
    def get_by_photo_id(session: Session, photo_id: uuid.UUID) -> FeatureVector | None:
        stmt = select(FeatureVector).where(FeatureVector.photo_id == photo_id)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create(
        session: Session,
        *,
        vector_id: uuid.UUID,
        photo_id: uuid.UUID,
        model_version: str,
        vector: list[float],
    ) -> FeatureVector:
        fv = FeatureVector(
            id=vector_id,
            photo_id=photo_id,
            model_version=model_version,
            vector=vector,
        )
        session.add(fv)
        session.flush()
        return fv
