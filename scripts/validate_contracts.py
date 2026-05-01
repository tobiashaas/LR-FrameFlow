#!/usr/bin/env python3
"""Validate OpenAPI + JSON Schemas (runs in CI and locally)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd)


def main() -> None:
    contracts = ROOT / "packages" / "contracts"
    openapi_file = contracts / "openapi" / "bridge-api.yaml"
    run([sys.executable, "-m", "openapi_spec_validator", str(openapi_file)])
    checks: list[tuple[str, str]] = [
        ("json-schema/job-train-request-v1.schema.json", "examples/job-train-request.example.json"),
        ("json-schema/job-envelope-v1.schema.json", "examples/job-envelope.example.json"),
    ]
    for schema, example in checks:
        run(
            [
                sys.executable,
                "-m",
                "check_jsonschema",
                "--schemafile",
                str(contracts / schema),
                str(contracts / example),
            ]
        )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
