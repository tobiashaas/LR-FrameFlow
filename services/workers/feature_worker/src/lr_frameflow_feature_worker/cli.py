"""Feature-stage worker: consumes edit jobs, forwards to inference queue."""

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
from lr_frameflow_queue.constants import QUEUE_FEATURE
from lr_frameflow_queue.publisher import RedisQueuePublisher, redis_from_env

log = get_logger("lr_ff.feature_worker")


def process_one() -> bool:
    """Returns True if an item was processed or invalid (non-idle), False on idle timeout."""
    redis = redis_from_env()
    publisher = RedisQueuePublisher(redis)
    factory = get_session_factory()

    envelope, raw = consumer.blpop_envelope(redis, QUEUE_FEATURE, timeout_seconds=5)
    if envelope is None and raw is None:
        return False
    if envelope is None and raw is not None:
        consumer.push_dead_letter(
            redis,
            primary_queue_name=QUEUE_FEATURE,
            raw_payload=raw,
            reason="invalid_envelope",
        )
        log.warning("dead-letter invalid envelope")
        return True

    if envelope.job_kind != "edit":
        consumer.push_dead_letter(
            redis,
            primary_queue_name=QUEUE_FEATURE,
            raw_payload=raw or "",
            reason=f"unexpected_job_kind:{envelope.job_kind}",
        )
        log.warning("wrong kind on feature queue job_kind=%s", envelope.job_kind)
        return True

    job_uuid = UUID(envelope.job_id)

    try:
        with session_scope(factory) as session:
            JobRepository.set_status(session, job_uuid, JobStatus.RUNNING)
        # Stub: real feature extraction would run here (CPU/GPU), then forward.
        publisher.forward_to_inference(envelope)
        log.info("forwarded job to inference job_id=%s", job_uuid)
    except Exception:
        tb = traceback.format_exc()[:4000]
        with session_scope(factory) as session:
            JobRepository.set_status(session, job_uuid, JobStatus.FAILED, failure_reason=tb)
        if raw is not None:
            consumer.push_dead_letter(
                redis,
                primary_queue_name=QUEUE_FEATURE,
                raw_payload=raw,
                reason="processing_error",
            )
        log.exception("feature worker failure job_id=%s", job_uuid)
    return True


def main() -> None:
    log.info("LR-FrameFlow feature worker — queue %s", QUEUE_FEATURE)
    while True:
        try:
            processed = process_one()
            if not processed:
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("Stopping feature worker", file=sys.stderr)
            raise SystemExit(0)


if __name__ == "__main__":
    main()
