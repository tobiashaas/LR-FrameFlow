from __future__ import annotations

import os

from redis import Redis

from lr_frameflow_domain.jobs import JobKind
from lr_frameflow_queue.constants import QUEUE_FEATURE, QUEUE_INFERENCE, QUEUE_TRAIN
from lr_frameflow_queue.envelope import JobEnvelopeV1


def redis_from_env(default_url: str = "redis://127.0.0.1:6379/0") -> Redis:
    return Redis.from_url(os.environ.get("REDIS_URL", default_url), decode_responses=True)


def first_stage_queue(kind: JobKind) -> str:
    if kind == JobKind.TRAIN:
        return QUEUE_TRAIN
    if kind == JobKind.EDIT:
        return QUEUE_FEATURE
    raise ValueError(kind)


class RedisQueuePublisher:
    def __init__(self, client: Redis) -> None:
        self._r = client

    def enqueue(self, envelope: JobEnvelopeV1) -> None:
        kind = JobKind(envelope.job_kind)
        q = first_stage_queue(kind)
        self._r.rpush(q, envelope.dumps())

    def forward_to_inference(self, envelope: JobEnvelopeV1) -> None:
        nxt = envelope.model_copy(update={"attempt": envelope.attempt + 1})
        self._r.rpush(QUEUE_INFERENCE, nxt.dumps())
