"""Training worker — consumes train jobs."""

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
from lr_frameflow_queue.constants import QUEUE_TRAIN
from lr_frameflow_queue.publisher import redis_from_env

log = get_logger("lr_ff.train_worker")


def process_one() -> bool:
    redis = redis_from_env()
    factory = get_session_factory()
    envelope, raw = consumer.blpop_envelope(redis, QUEUE_TRAIN, timeout_seconds=5)
    if envelope is None and raw is None:
        return False
    if envelope is None and raw is not None:
        consumer.push_dead_letter(
            redis,
            primary_queue_name=QUEUE_TRAIN,
            raw_payload=raw,
            reason="invalid_envelope",
        )
        return True

    if envelope.job_kind != "train":
        consumer.push_dead_letter(
            redis,
            primary_queue_name=QUEUE_TRAIN,
            raw_payload=raw or "",
            reason=f"unexpected_job_kind:{envelope.job_kind}",
        )
        return True

    job_uuid = UUID(envelope.job_id)
    try:
        with session_scope(factory) as session:
            JobRepository.set_status(session, job_uuid, JobStatus.RUNNING)
            # Stub: replace with real training pipeline (GPU worker).
            JobRepository.set_status(session, job_uuid, JobStatus.COMPLETED)
        log.info("train job completed job_id=%s", job_uuid)
    except Exception:
        tb = traceback.format_exc()[:4000]
        with session_scope(factory) as session:
            JobRepository.set_status(session, job_uuid, JobStatus.FAILED, failure_reason=tb)
        if raw is not None:
            consumer.push_dead_letter(
                redis,
                primary_queue_name=QUEUE_TRAIN,
                raw_payload=raw,
                reason="processing_error",
            )
        log.exception("train worker failure job_id=%s", job_uuid)
    return True


def main() -> None:
    log.info("LR-FrameFlow train worker — queue %s", QUEUE_TRAIN)
    while True:
        try:
            if not process_one():
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("Stopping train worker", file=sys.stderr)
            raise SystemExit(0)


if __name__ == "__main__":
    main()
