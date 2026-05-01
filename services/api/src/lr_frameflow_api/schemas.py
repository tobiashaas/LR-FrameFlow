"""Pydantic request/response models aligned with packages/contracts."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TrainSchema = Literal["train-request-v1"]
EditSchema = Literal["edit-request-v1"]


class TrainJobRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: TrainSchema
    correlation_id: str | None = None
    profile_name: str
    genre: str
    format_type: Literal["raw", "jpeg_tiff"]
    color_type: Literal["color", "bw"]
    photo_ids: Annotated[list[UUID], Field(min_length=1)]
    base_preset: dict[str, Any] | None = None


class EditJobRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: EditSchema
    correlation_id: str | None = None
    profile_id: UUID
    collection_name: str | None = None
    photo_ids: Annotated[list[UUID], Field(min_length=1)]


class JobAcceptedResponse(BaseModel):
    job_id: UUID
    status: Literal["queued"] = "queued"
    kind: Literal["train", "edit"]


class JobSnapshotResponse(BaseModel):
    job_id: UUID
    status: Literal["queued", "running", "completed", "failed"]
    payload_schema_version: str | None = None
    correlation_id: str | None = None
