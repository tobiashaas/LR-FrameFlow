"""Inference worker — applies profile model to photos and saves EditResults."""

from __future__ import annotations

import os
import sys
import time
import traceback
from uuid import UUID, uuid4

import boto3
from redis import Redis
from sqlalchemy.orm import sessionmaker

from lr_frameflow_domain.jobs import JobStatus
from lr_frameflow_inference_pipeline import run_inference
from lr_frameflow_observability import get_logger, start_heartbeat_thread
from lr_frameflow_persistence.reaper import reap_stuck_jobs, start_reaper_thread
from lr_frameflow_persistence.repositories.edit_results import EditResultRepository
from lr_frameflow_persistence.repositories.feature_vectors import FeatureVectorRepository
from lr_frameflow_persistence.repositories.jobs import JobRepository
from lr_frameflow_persistence.repositories.profiles import ProfileRepository
from lr_frameflow_persistence.session import get_session_factory, session_scope
from lr_frameflow_queue import consumer
from lr_frameflow_queue.constants import QUEUE_INFERENCE
from lr_frameflow_queue.publisher import RedisQueuePublisher, redis_from_env

log = get_logger("lr_ff.inference_worker")


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minio"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "miniosecret_changeme"),
        region_name="us-east-1",
    )



def process_one(redis: Redis, factory: sessionmaker) -> bool:
    envelope, raw = consumer.blpop_envelope(redis, QUEUE_INFERENCE, timeout_seconds=5)
    if envelope is None and raw is None:
        return False
    if envelope is None:
        consumer.push_dead_letter(redis, primary_queue_name=QUEUE_INFERENCE, raw_payload=raw, reason="invalid_envelope")
        return True

    if envelope.job_kind != "edit":
        consumer.push_dead_letter(redis, primary_queue_name=QUEUE_INFERENCE, raw_payload=raw or "", reason=f"unexpected_job_kind:{envelope.job_kind}")
        return True

    job_uuid = UUID(envelope.job_id)
    profile_id_str = envelope.payload.get("profile_id")
    photo_ids = [UUID(pid) for pid in envelope.payload.get("photo_ids", [])]

    try:
        with session_scope(factory) as session:
            JobRepository.set_status(session, job_uuid, JobStatus.RUNNING)

        if not profile_id_str:
            raise ValueError("missing profile_id in payload")
        profile_id = UUID(profile_id_str)

        # Load profile + model artifact
        with session_scope(factory) as session:
            profile = ProfileRepository.get_by_id(session, profile_id)
            if profile is None:
                raise ValueError(f"profile {profile_id} not found")
            artifact_key = profile.model_artifact_key

        model_bytes: bytes = b""
        if artifact_key:
            try:
                s3 = _s3_client()
                bucket = os.environ.get("S3_BUCKET", "lrff-photos")
                obj = s3.get_object(Bucket=bucket, Key=artifact_key)
                model_bytes = obj["Body"].read()
            except Exception as e:
                log.warning("could not load model artifact key=%s: %s — using zero predictions", artifact_key, e)

        # Run inference for each photo
        for photo_id in photo_ids:
            with session_scope(factory) as session:
                fv = FeatureVectorRepository.get_by_photo_id(session, photo_id)
                vector = list(fv.vector) if fv is not None else [0.0] * 128

                lr_settings = run_inference(model_bytes, vector) if model_bytes else {p: 0.0 for p in ["exposure", "temp", "tint", "contrast", "highlights", "shadows", "whites", "blacks", "vibrance", "saturation"]}

                EditResultRepository.create(
                    session,
                    result_id=uuid4(),
                    job_id=job_uuid,
                    photo_id=photo_id,
                    profile_id=profile_id,
                    lr_settings=lr_settings,
                )
            log.info("inference done photo_id=%s job_id=%s", photo_id, job_uuid)

        with session_scope(factory) as session:
            JobRepository.set_status(session, job_uuid, JobStatus.COMPLETED)

        log.info("inference job completed job_id=%s photos=%d", job_uuid, len(photo_ids))

    except Exception:
        tb = traceback.format_exc()[:4000]
        with session_scope(factory) as session:
            JobRepository.set_status(session, job_uuid, JobStatus.FAILED, failure_reason=tb)
        if raw is not None:
            consumer.push_dead_letter(redis, primary_queue_name=QUEUE_INFERENCE, raw_payload=raw, reason="processing_error")
        log.exception("inference worker failure job_id=%s", job_uuid)

    return True


def main() -> None:
    log.info("LR-FrameFlow inference worker — queue %s", QUEUE_INFERENCE)
    redis = redis_from_env()
    publisher = RedisQueuePublisher(redis)
    factory = get_session_factory()

    start_heartbeat_thread("/tmp/lr_ff_inference_worker.heartbeat")

    n = reap_stuck_jobs(factory, queue_name=QUEUE_INFERENCE, publisher=publisher)
    if n:
        log.warning("reaper: recovered %d stuck jobs at startup", n)
    start_reaper_thread(factory, queue_name=QUEUE_INFERENCE, publisher=publisher, logger=log)

    while True:
        try:
            if not process_one(redis, factory):
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("Stopping inference worker", file=sys.stderr)
            raise SystemExit(0)


if __name__ == "__main__":
    main()
