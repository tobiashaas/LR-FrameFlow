"""Inference worker — final stage for edit jobs."""

from __future__ import annotations

import sys
import time
import traceback
from uuid import UUID

from lr_frameflow_domain.jobs import JobStatus
from lr_frameflow_observability import get_logger
from lr_frameflow_persistence.repositories.jobs import JobRepository
from lr_frameflow_persistence.session import get_session_factory, session_scope
from lr_frameflow_queue import consumer
from lr_frameflow_queue.constants import QUEUE_INFERENCE
from lr_frameflow_queue.publisher import redis_from_env
from lr_frameflow_inference_pipeline import run_default_stub

log = get_logger("lr_ff.inference_worker")


def process_one() -> bool:
    redis = redis_from_env()
    factory = get_session_factory()
    envelope, raw = consumer.blpop_envelope(redis, QUEUE_INFERENCE, timeout_seconds=5)
    if envelope is None and raw is None:
        return False
    if envelope is None and raw is not None:
        consumer.push_dead_letter(
            redis,
            primary_queue_name=QUEUE_INFERENCE,
            raw_payload=raw,
            reason="invalid_envelope",
        )
        return True

    if envelope.job_kind != "edit":
        consumer.push_dead_letter(
            redis,
            primary_queue_name=QUEUE_INFERENCE,
            raw_payload=raw or "",
            reason=f"unexpected_job_kind:{envelope.job_kind}",
        )
        return True

    job_uuid = UUID(envelope.job_id)
    try:
        with session_scope(factory) as session:
            JobRepository.set_status(session, job_uuid, JobStatus.RUNNING)
            _ = run_default_stub(envelope.payload)
            JobRepository.set_status(session, job_uuid, JobStatus.COMPLETED)
        log.info("inference job completed job_id=%s", job_uuid)
    except Exception:
        tb = traceback.format_exc()[:4000]
        with session_scope(factory) as session:
            JobRepository.set_status(session, job_uuid, JobStatus.FAILED, failure_reason=tb)
        if raw is not None:
            consumer.push_dead_letter(
                redis,
                primary_queue_name=QUEUE_INFERENCE,
                raw_payload=raw,
                reason="processing_error",
            )
        log.exception("inference worker failure job_id=%s", job_uuid)
    return True


def main() -> None:
    log.info("LR-FrameFlow inference worker — queue %s", QUEUE_INFERENCE)
    while True:
        try:
            if not process_one():
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("Stopping inference worker", file=sys.stderr)
            raise SystemExit(0)


if __name__ == "__main__":
    main()
