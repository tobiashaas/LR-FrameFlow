# ADR 003 — Redis Listen, DLQ und Import-Regeln

- **Status:** Akzeptiert
- **Datum:** 2026-05-01
- **Entscheider:** Maintainer

## Kontext

Jobs müssen zwischen API und mehreren Worker-Prozessen zuverlässig transportiert werden; fehlerhafte Payloads und Exceptions dürfen nicht silent verworfen werden.

## Entscheidung — Redis-Topologie

- **Transport:** Redis **Listen** mit `RPUSH` / `BLPOP` und bekannten Schlüsseln [`QUEUE_TRAIN`](../../libs/queue/src/lr_frameflow_queue/constants.py), `lrff:jobs:feature`, `lrff:jobs:inference` (siehe `libs/lr_frameflow_queue`).
- **Routing:** `train` landet direkt auf `lrff:jobs:train`; `edit` erstmals auf `lrff:jobs:feature`, der Feature-Worker leitet nach erfolgreichem Stub-Schritt per `forward_to_inference` auf `lrff:jobs:inference` weiter.
- **DLQ:** Jede primäre Queue besitzt einen Dead-Letter Key `primary:dlq`; ungültige Envelopes sowie harte Verarbeitungsfehler werden mit JSON-Metadaten dort abgelegt (siehe `push_dead_letter` in `lr_frameflow_queue.consumer`).
- **Evolution:** Streams/Consumer-Groups oder ein Orchestrierungs-Framework (Temporal etc.) bleiben hinter einer Publisher/Consumer-Abstraktion in `libs/queue` austauschbar.

## Entscheidung — Modul-Import-Matrix

| Modul | Erlaubte Abhängigkeiten |
|-------|-------------------------|
| `lr_frameflow_domain` | keine internen LR-Pakete |
| `lr_frameflow_queue` | domain, pydantic, redis |
| `lr_frameflow_persistence` | domain, sqlalchemy/psycopg |
| `lr_frameflow_inference_pipeline` | nur stdlib optional numpy/torch später |
| `lr_frameflow_observability` | stdlib logging |
| `services/api` | domain, persistence, queue (keine Worker, kein torch) |
| `services/workers/*` | domain, persistence, queue, observability, ggf. inference-pipeline |

Verbote: Worker importieren **nicht** `lr_frameflow_api`; API importiert **nicht** Worker-Module.

## Folgen / Trade-offs

- **Positiv:** Einfaches Debugging, minimale Betriebsüberraschungen, klarer Eskalationspfad via DLQ und `jobs.failure_reason`.
- **Negativ:** Listen bieten weniger eingebaute Retries als Streams; horizontale Skalierung erfordert eigene Idempotenz beim Verbrauch (hier: `job_id` + Status in Postgres).
