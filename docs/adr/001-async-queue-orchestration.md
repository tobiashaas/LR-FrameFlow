# ADR 001 — Asynchrone Job-Orchestrierung über Queue

- **Status:** Akzeptiert
- **Datum:** 2026-05-01
- **Entscheider:** Maintainer

## Kontext

Die Lightroom-Pipeline besteht aus teuren Schritten (Features, Embedding, Retrieval, Inferenz). Ein synchron blockierender FastAPI-Handler würde Timeouts riskieren und Skalierung verhindern.

## Entscheidung

- FastAPI gibt **HTTP 202** mit `job_id` zurück und persistiert Payload + Zustände in Postgres (`jobs` später via Migrationen).
- Lang laufende Schritte laufen **asynchron** in dedizierten **Worker-Prozessen**, angebunden über **Redis als Queue** (`REDIS_URL` in [`infra/compose/env.example`](../../infra/compose/env.example)). Alternativen wie Temporal können später ohne Verlust der Modularität evaluiert werden.

## Folgen / Trade-offs

- **Positiv:** Horizontales Skalieren für `inference_worker`, saubere Trennung API vs. Arbeit, weniger kopplende Retries möglich (Idempotency-Key Header).
- **Negativ:** Zusätzlicher Betrieb (Redis), erhöhte Komplexität lokal gegenüber allem-in-Prozess — entspricht jedoch dem Skalierungsziel aus dem Produktkonzept.
