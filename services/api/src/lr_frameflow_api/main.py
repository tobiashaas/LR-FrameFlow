"""FastAPI entrypoint — persist jobs and enqueue envelopes (no heavy work here)."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from lr_frameflow_api.deps import get_publisher, get_session
from lr_frameflow_api.schemas import (
    EditJobRequestV1,
    JobAcceptedResponse,
    JobSnapshotResponse,
    TrainJobRequestV1,
)
from lr_frameflow_domain.jobs import JobKind
from lr_frameflow_persistence.repositories.jobs import JobRepository
from lr_frameflow_queue.envelope import JobEnvelopeV1
from lr_frameflow_queue.publisher import RedisQueuePublisher

app = FastAPI(title="LR-FrameFlow API", version="0.1.1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/jobs/train", status_code=202, response_model=JobAcceptedResponse)
def create_train_job(
    body: TrainJobRequestV1,
    session: Session = Depends(get_session),
    publisher: RedisQueuePublisher = Depends(get_publisher),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    norm_key = (idempotency_key or "").strip() or None
    if norm_key:
        existing = JobRepository.get_by_idempotency_key(session, norm_key)
        if existing:
            if existing.kind != JobKind.TRAIN.value:
                raise HTTPException(status_code=409, detail="idempotency key conflicts with another job kind")
            return JobAcceptedResponse(job_id=existing.id, kind="train")

    job_id = uuid4()
    JobRepository.create(
        session,
        job_id=job_id,
        kind=JobKind.TRAIN,
        payload_schema_version=body.schema_version,
        payload=body.model_dump(mode="json"),
        correlation_id=body.correlation_id,
        idempotency_key=norm_key,
    )

    trace = {}
    if body.correlation_id:
        trace["correlation_id"] = body.correlation_id
    envelope = JobEnvelopeV1(
        job_id=str(job_id),
        job_kind="train",
        payload=body.model_dump(mode="json"),
        trace_context=trace,
    )
    publisher.enqueue(envelope)
    return JobAcceptedResponse(job_id=job_id, kind="train")


@app.post("/v1/jobs/edit", status_code=202, response_model=JobAcceptedResponse)
def create_edit_job(
    body: EditJobRequestV1,
    session: Session = Depends(get_session),
    publisher: RedisQueuePublisher = Depends(get_publisher),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    norm_key = (idempotency_key or "").strip() or None
    if norm_key:
        existing = JobRepository.get_by_idempotency_key(session, norm_key)
        if existing:
            if existing.kind != JobKind.EDIT.value:
                raise HTTPException(status_code=409, detail="idempotency key conflicts with another job kind")
            return JobAcceptedResponse(job_id=existing.id, kind="edit")

    job_id = uuid4()
    JobRepository.create(
        session,
        job_id=job_id,
        kind=JobKind.EDIT,
        payload_schema_version=body.schema_version,
        payload=body.model_dump(mode="json"),
        correlation_id=body.correlation_id,
        idempotency_key=norm_key,
    )

    trace = {}
    if body.correlation_id:
        trace["correlation_id"] = body.correlation_id
    envelope = JobEnvelopeV1(
        job_id=str(job_id),
        job_kind="edit",
        payload=body.model_dump(mode="json"),
        trace_context=trace,
    )
    publisher.enqueue(envelope)
    return JobAcceptedResponse(job_id=job_id, kind="edit")


@app.get("/v1/jobs/{job_id}", response_model=JobSnapshotResponse)
def get_job(job_id: UUID, session: Session = Depends(get_session)):
    record = JobRepository.get_by_id(session, job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobSnapshotResponse(
        job_id=record.id,
        status=record.status,  # type: ignore[arg-type]
        payload_schema_version=record.payload_schema_version,
        correlation_id=record.correlation_id,
    )
