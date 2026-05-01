# LR-FrameFlow

Modulares System zur **KI-gestützten Lightroom-Classic-Bearbeitung**: Lightroom-Plugin für Workflow und Review, **Bridge-Desktop-App** für lokale Orchestrierung, **Thin-API** (FastAPI) und **Worker** für Features, Training und Inferenz mit klar versioniertem **Contract** zwischen allen Teilen.

- **Upstream:** [github.com/tobiashaas/LR-FrameFlow](https://github.com/tobiashaas/LR-FrameFlow)

## Architektur (Kurz)

```text
Lightroom Plugin (Lua) → Bridge (Desktop) → API → Job Queue → Worker (Feature / Train / Inference)
                                                                    ↓
                                              Postgres (+ pgvector), Objekt-Speicher
```

Siehe Paketgrenzen und Entscheide in [`docs/adr/`](docs/adr/).

## Repository-Layout

```text
apps/
  lr-plugin/           # Lightroom Classic SDK Plugin (Lua)
  bridge/               # Lokale Bridge-App (Tauri – siehe ADR)

packages/
  contracts/           # JSON Schema + OpenAPI (Bridge ↔ API); CI soll Contract-Tests fahren

services/
  api/                  # FastAPI-Gateway (Jobs, keine schwere Inferenz im Request-Pfad)
  workers/             # Feature-, Train-, Inference-Worker (skalierbar)

libs/
  edit-serializer/     # Lightroom-kompatibles Writeback (reine Transformation)
  lr-io/                # Gemeinsame I/O-/Pfadhilfen

infra/
  compose/             # lokale Postgres (pgvector), Redis, MinIO
  migrations/           # Datenbankmigrationen

docs/
  adr/                  # Architecture Decision Records
```

## Contracts & CI

- Quelle der API- und Datenformate: [`packages/contracts/`](packages/contracts/) (OpenAPI + JSON Schema).
- **Empfehlung:** In CI einen Schritt ergänzen, der Schemas validiert (`openapi-spec-validator`, `check-jsonschema`) sowie **Contract-Tests** zwischen Bridge-Client-Stubs und generierten Typen aus der Spec — noch nicht automatisiert, aber im Spec-Ordner dokumentiert.

## Lokale Infra starten

Voraussetzung: [Docker Compose](https://docs.docker.com/compose/).

```bash
cd infra/compose
docker compose up -d
```

Umgebungsvariablen: siehe Kommentare in [`infra/compose/docker-compose.yml`](infra/compose/docker-compose.yml). Für die API/Worker liegt eine Beispieldatei in [`infra/compose/env.example`](infra/compose/env.example).

## Python-Komponenten

Jede Python-Komponente hat ein eigenes `pyproject.toml` (klare Ownership). Reihenfolge wegen Abhängigkeiten des Inference-Workers:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e "libs/edit-serializer" -e "libs/lr-io"
pip install -e "services/api[dev]"
pip install -e "services/workers/feature_worker" -e "services/workers/train_worker"
pip install -e "services/workers/inference_worker"

cd services/api
uvicorn lr_frameflow_api.main:app --reload
```

## Bridge (Tauri)

Ordner [`apps/bridge`](apps/bridge): minimales Gerüst; vollständige App mit `pnpm create tauri-app` ergänzen (siehe `apps/bridge/README.md`).

## Lizenz

Sofern nicht anders gekennzeichnet, siehe Repo-Root `LICENSE` (optional ergänzen).
