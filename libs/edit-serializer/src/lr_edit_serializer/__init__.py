"""Serialize internal edit payloads toward Lightroom-compatible sidecars/metadata."""

from typing import Any, Mapping


def serialize_for_lightroom(edit: Mapping[str, Any]) -> Mapping[str, Any]:
    """Stub: passes through validated structure until XMP/catalog mapping lands."""
    return dict(edit)


def ping() -> str:
    return "edit-serializer"
