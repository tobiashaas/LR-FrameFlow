"""Training worker — trains a profile model from photo feature vectors."""

from __future__ import annotations

import os
import sys
import time
import traceback
from uuid import UUID

import boto3
from redis import Redis
from sqlalchemy.orm import sessionmaker

from lr_frameflow_domain.jobs import JobStatus
from lr_frameflow_domain.profiles import ProfileStatus
from lr_frameflow_inference_pipeline import train_model
from lr_frameflow_observability import get_logger
from lr_frameflow_persistence.repositories.feature_vectors import FeatureVectorRepository
from lr_frameflow_persistence.repositories.jobs import JobRepository
from lr_frameflow_persistence.repositories.photos import PhotoRepository
from lr_frameflow_persistence.repositories.profiles import ProfileRepository
from lr_frameflow_persistence.session import get_session_factory, session_scope
from lr_frameflow_queue import consumer
from lr_frameflow_queue.constants import QUEUE_TRAIN
from lr_frameflow_queue.publisher import redis_from_env

log = get_logger("lr_ff.train_worker")


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minio"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "miniosecret_changeme"),
        region_name="us-east-1",
    )


def _ensure_bucket(s3, bucket: str) -> None:
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        s3.create_bucket(Bucket=bucket)



def process_one(redis: Redis, factory: sessionmaker) -> bool:
    envelope, raw = consumer.blpop_envelope(redis, QUEUE_TRAIN, timeout_seconds=5)
    if envelope is None and raw is None:
        return False
    if envelope is None:
        consumer.push_dead_letter(redis, primary_queue_name=QUEUE_TRAIN, raw_payload=raw, reason="invalid_envelope")
        return True

    if envelope.job_kind != "train":
        consumer.push_dead_letter(redis, primary_queue_name=QUEUE_TRAIN, raw_payload=raw or "", reason=f"unexpected_job_kind:{envelope.job_kind}")
        return True

    job_uuid = UUID(envelope.job_id)
    profile_id_str = envelope.payload.get("profile_id")
    photo_ids = [UUID(pid) for pid in envelope.payload.get("photo_ids", [])]
    base_preset = envelope.payload.get("base_preset")

    try:
        with session_scope(factory) as session:
            JobRepository.set_status(session, job_uuid, JobStatus.RUNNING)
            if profile_id_str:
                ProfileRepository.set_status(session, UUID(profile_id_str), ProfileStatus.TRAINING)

        # Load feature vectors + LR settings for all training photos
        feature_vectors: list[list[float]] = []
        lr_settings_list: list[dict] = []
        with session_scope(factory) as session:
            for photo_id in photo_ids:
                fv = FeatureVectorRepository.get_by_photo_id(session, photo_id)
                if fv is None:
                    log.warning("no feature vector for photo_id=%s — skipping", photo_id)
                    continue
                photo = PhotoRepository.get_by_id(session, photo_id)
                lr_settings = (photo.lr_develop_settings or {}) if photo else {}
                feature_vectors.append(list(fv.vector))
                lr_settings_list.append(lr_settings)

        if not feature_vectors:
            raise ValueError(f"no feature vectors available for job {job_uuid} — run feature extraction first")

        # Train real model and save bytes to MinIO
        model_bytes = train_model(feature_vectors, lr_settings_list)
        profile_id = UUID(profile_id_str) if profile_id_str else None
        artifact_key = f"models/{profile_id}/model-ridge-v1.joblib" if profile_id else f"models/job-{job_uuid}/model-ridge-v1.joblib"
        bucket = os.environ.get("S3_BUCKET", "lrff-photos")

        s3 = _s3_client()
        _ensure_bucket(s3, bucket)
        s3.put_object(Bucket=bucket, Key=artifact_key, Body=model_bytes, ContentType="application/octet-stream")
        log.info("model artifact saved key=%s n_samples=%d", artifact_key, len(feature_vectors))

        # Update profile: artifact key + status ready
        with session_scope(factory) as session:
            if profile_id:
                ProfileRepository.set_artifact(session, profile_id, model_artifact_key=artifact_key)
                ProfileRepository.set_status(session, profile_id, ProfileStatus.READY)
            JobRepository.set_status(session, job_uuid, JobStatus.COMPLETED)

        log.info("train job completed job_id=%s profile_id=%s", job_uuid, profile_id)

    except Exception:
        tb = traceback.format_exc()[:4000]
        with session_scope(factory) as session:
            JobRepository.set_status(session, job_uuid, JobStatus.FAILED, failure_reason=tb)
            if profile_id_str:
                ProfileRepository.set_status(session, UUID(profile_id_str), ProfileStatus.FAILED, failure_reason=tb[:512])
        if raw is not None:
            consumer.push_dead_letter(redis, primary_queue_name=QUEUE_TRAIN, raw_payload=raw, reason="processing_error")
        log.exception("train worker failure job_id=%s", job_uuid)

    return True


def main() -> None:
    log.info("LR-FrameFlow train worker — queue %s", QUEUE_TRAIN)
    redis = redis_from_env()
    factory = get_session_factory()
    while True:
        try:
            if not process_one(redis, factory):
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("Stopping train worker", file=sys.stderr)
            raise SystemExit(0)


if __name__ == "__main__":
    main()
