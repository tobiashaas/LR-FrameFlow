# lr-frameflow-queue

Redis Listen (`RPUSH`/`BLPOP`) und **`JobEnvelopeV1`** — kanonisches Schema unter [`packages/contracts/json-schema/job-envelope-v1.schema.json`](../../packages/contracts/json-schema/job-envelope-v1.schema.json).

## Totbuch / DLQ

Jede primäre Queue `lrff:jobs:*` besitzt einen Dead-Letter-Key `{queue}:dlq`. Ungültige Payloads beim Parsen sowie harte Fehler beim Verarbeiten landen dort (siehe `lr_frameflow_queue.consumer.push_dead_letter`) — Entscheide in [ADR 003](../../docs/adr/003-redis-dlq-and-import-rules.md).
