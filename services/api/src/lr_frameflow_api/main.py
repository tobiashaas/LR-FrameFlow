"""FastAPI entrypoint — routes enqueue work; heavy processing stays in workers."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Header

app = FastAPI(title="LR-FrameFlow API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/jobs/train", status_code=202)
def create_train_job(
    payload: dict,
    idempotency_key: str | None = Header(default=None),
):
    _ = payload
    job_id = str(uuid4())
    return {"job_id": job_id, "status": "queued", "kind": "train"}


@app.post("/v1/jobs/edit", status_code=202)
def create_edit_job(
    payload: dict,
    idempotency_key: str | None = Header(default=None),
):
    _ = payload
    job_id = str(uuid4())
    return {"job_id": job_id, "status": "queued", "kind": "edit"}


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str):
    return {"job_id": job_id, "status": "queued"}
