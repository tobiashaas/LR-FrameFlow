"""Injectable inference pipeline (stub implementations for now)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

Step = Callable[[dict[str, Any]], dict[str, Any]]


def step_normalize(ctx: dict[str, Any]) -> dict[str, Any]:
    out = dict(ctx)
    out["stage"] = "normalized"
    return out


def step_extract_features(ctx: dict[str, Any]) -> dict[str, Any]:
    out = dict(ctx)
    out["features"] = {"luma_mean": 0.42}
    return out


def step_classify_scene(ctx: dict[str, Any]) -> dict[str, Any]:
    out = dict(ctx)
    out["scene"] = {"scene_type": "portrait", "confidence": 0.5}
    return out


def step_embed(ctx: dict[str, Any]) -> dict[str, Any]:
    out = dict(ctx)
    out["embedding_dim"] = 8
    return out


def step_retrieve_neighbors(ctx: dict[str, Any]) -> dict[str, Any]:
    out = dict(ctx)
    out["neighbors"] = []
    return out


def step_predict_deltas(ctx: dict[str, Any]) -> dict[str, Any]:
    out = dict(ctx)
    out["deltas"] = {"exposure": 0.0}
    return out


def step_confidence(ctx: dict[str, Any]) -> dict[str, Any]:
    out = dict(ctx)
    out["confidence"] = {"score": 0.5, "review_needed": False}
    return out


DEFAULT_STEPS: Sequence[Step] = (
    step_normalize,
    step_extract_features,
    step_classify_scene,
    step_embed,
    step_retrieve_neighbors,
    step_predict_deltas,
    step_confidence,
)


def run_pipeline(steps: Sequence[Step], payload: dict[str, Any]) -> dict[str, Any]:
    ctx: dict[str, Any] = {"payload": payload}
    for step in steps:
        ctx = step(ctx)
    return ctx


def run_default_stub(payload: dict[str, Any]) -> dict[str, Any]:
    return run_pipeline(DEFAULT_STEPS, payload)
