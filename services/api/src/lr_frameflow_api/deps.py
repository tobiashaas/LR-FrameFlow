from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session

from lr_frameflow_persistence.session import get_session_factory, session_scope
from lr_frameflow_queue.publisher import RedisQueuePublisher, redis_from_env


@lru_cache(maxsize=1)
def session_factory_holder():
    return get_session_factory()


def get_session() -> Generator[Session, None, None]:
    factory = session_factory_holder()
    with session_scope(factory) as session:
        yield session


def get_publisher() -> RedisQueuePublisher:
    # Not cached intentionally to respect env mocks in tests; cheap construction.
    return RedisQueuePublisher(redis_from_env())
