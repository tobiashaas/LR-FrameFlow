# MVP Plan — LRFrameFlow

**Stand:** 2026-05-15  
**Ziel:** Vollständig funktionierendes System vom LR-Plugin bis zur Rückspielung der Develop-Settings, mit echter ML-Pipeline — schrittweise aufgebaut, nie blind.

---

## Leitprinzipien

- **Domain first.** Bevor Code entsteht, steht das Datenmodell. Alles andere leitet sich daraus ab.
- **End-to-End vor Perfektion.** Jede Phase endet mit einem lauffähigen, testbaren System — kein toter Code.
- **Stubs sind okay, Lücken nicht.** Ein Stub der echte Daten durch echte Infrastruktur schickt ist besser als perfekter Code der nirgendwo angeschlossen ist.
- **Contracts sind heilig.** JSON-Schema und OpenAPI werden vor der Implementierung aktualisiert, nicht danach.

---

## Domain-Modell (beschlossen, gilt für alle Phasen)

```
Photo
├── id                    UUID, intern vergeben
├── lr_catalog_uuid       String — von LR Classic vergeben, stabiler Identifier
├── s3_key                String — Pfad der JPEG-Preview in MinIO
├── exif_snapshot         JSONB — Kamera, ISO, Belichtung, Brennweite etc.
├── lr_develop_settings   JSONB — aktuelle LR-Einstellungen beim Export (Baseline)
├── feature_vector_id     → FeatureVector (nullable, null bis extrahiert)
└── created_at

FeatureVector
├── id                    UUID
├── photo_id              → Photo
├── model_version         String — Versionierung des Extraktions-Algorithmus
├── vector                pgvector — Dimension abhängig von model_version
└── created_at

Profile
├── id                    UUID
├── name                  String
├── genre                 String (wedding, portrait, landscape, …)
├── format_type           "raw" | "jpeg_tiff"
├── color_type            "color" | "bw"
├── status                "draft" | "training" | "ready" | "failed"
├── version               Int — hochzählen bei Retraining
├── base_preset           JSONB — optionaler LR-Preset als Startpunkt
├── model_artifact_key    String nullable — S3-Key der gespeicherten Modellgewichte
├── lr_output_keys        JSONB — welche LR-Parameter dieses Profil vorhersagt
│                                 z.B. ["exposure", "contrast", "highlights", ...]
├── failure_reason        String nullable
└── created_at / updated_at

Job (Erweiterung bestehend)
└── profile_id            → Profile (nullable, required für Edit-Jobs)
```

**Kernentscheidungen:**
- Feature-Vektoren sind **Photo-unabhängig von Profilen** — einmal berechnen, beliebig oft nutzen
- Ein Profil speichert **sowohl** ML-Gewichte (MinIO) **als auch** LR-Parameter-Template (DB)
- Fotos werden über `lr_catalog_uuid` identifiziert — LR ist die Quelle der Wahrheit für IDs
- Zurückspielen = LR Develop Settings als JSON, niemals RAW-Manipulation

---

## Datenfluss (Gesamtbild)

```
┌─────────────┐    Preview+Meta    ┌────────┐    HTTP POST    ┌─────┐
│  LR Plugin  │ ─────────────────▶ │ Bridge │ ─────────────▶ │ API │
│   (Lua)     │                    │(Tauri) │                 │     │
│             │ ◀───────────────── │        │ ◀───────────── │     │
└─────────────┘   Develop Settings └────────┘   Job Status   └──┬──┘
                                                                  │
                    ┌─────────────────────────────────────────────┘
                    │
         ┌──────────▼──────────────────────────────────────────────┐
         │                   Redis Queues                           │
         │  lrff:jobs:feature  →  lrff:jobs:inference              │
         │  lrff:jobs:train                                         │
         └──────┬──────────────────────────┬────────────────────────┘
                │                          │
     ┌──────────▼──────────┐   ┌───────────▼────────────────────────┐
     │   Feature Worker    │   │         Train Worker               │
     │                     │   │                                    │
     │ 1. Lade Preview      │   │ 1. Lade Photo-Features            │
     │    aus MinIO        │   │ 2. Trainiere Modell                │
     │ 2. Extrahiere       │   │ 3. Speichere Gewichte → MinIO      │
     │    Features         │   │ 4. Update Profile → ready          │
     │ 3. Speichere        │   └────────────────────────────────────┘
     │    pgvector         │
     │ 4. Forward →        │   ┌────────────────────────────────────┐
     │    inference queue  │   │       Inference Worker             │
     └─────────────────────┘   │                                    │
                                │ 1. Lade Profil + Gewichte         │
                                │ 2. Lade Feature-Vektor            │
                                │ 3. Berechne LR-Settings           │
                                │ 4. Speichere Result → DB/MinIO    │
                                │ 5. Job → completed                 │
                                └────────────────────────────────────┘
```

---

## Phase 1 — Domain Foundation

**Ziel:** Vollständiges DB-Schema, Domain-Modelle, aktualisierte Contracts. Kein Worker-Code, kein ML. Aber echte Tabellen, echte Migrations, echte Schemas.

### 1.1 Domain Library (`libs/domain`)

- `Photo`, `FeatureVector`, `Profile` als Pydantic-Modelle / Enums
- `ProfileStatus` Enum: `draft | training | ready | failed`
- Erweitere `JobKind` falls nötig

### 1.2 Persistence (`libs/persistence`)

Neue SQLAlchemy-Modelle:

```python
# models.py Ergänzungen
class Photo(Base): ...
class FeatureVector(Base): ...
class Profile(Base): ...
```

`Job`-Modell erweitern:
- `profile_id: UUID | None` (FK → profiles)
- `started_at: datetime | None` (für Stuck-Job-Detection, Phase 4)

Neue Repositories:
- `PhotoRepository`: create, get_by_lr_uuid, get_by_id
- `ProfileRepository`: create, get_by_id, set_status, set_artifact
- `FeatureVectorRepository`: create, get_by_photo_id

### 1.3 Migrations (`infra/migrations`)

```
002_create_photos.py
003_create_profiles.py
004_create_feature_vectors.py
005_add_profile_id_to_jobs.py
006_add_started_at_to_jobs.py
```

### 1.4 Contracts aktualisieren (`packages/contracts`)

JSON Schemas aktualisieren/erstellen:
- `job-train-request-v1.schema.json` — bereits vorhanden, bleibt
- `job-edit-request-v1.schema.json` — bereits vorhanden, bleibt
- `photo-upload-v1.schema.json` — **neu**: was das Plugin ans Backend schickt
- `edit-result-v1.schema.json` — **neu**: LR Develop Settings die zurückgegeben werden

OpenAPI `bridge-api.yaml` erweitern:
- `POST /v1/photos` — Photo hochladen (Preview + Metadata)
- `GET /v1/profiles` — Liste aller Profile
- `GET /v1/profiles/{profile_id}` — Profil-Status

### 1.5 API-Routen (`services/api`)

Neue Endpoints:
- `POST /v1/photos` — nimmt Multipart (JPEG Preview + JSON Metadata), lädt in MinIO, erstellt `Photo`-Record, gibt `photo_id` zurück
- `GET /v1/profiles` — listet Profile
- `GET /v1/profiles/{profile_id}` — Profil-Details inkl. Status

`POST /v1/jobs/edit` anpassen:
- muss `profile_id` validieren (existiert das Profil? ist es `ready`?)
- muss `photo_ids` auf bekannte Photos prüfen

**Deliverable:** `docker compose up` → Migrations laufen durch → alle Endpoints erreichbar → Contracts validieren in CI.

---

## Phase 2 — End-to-End Pipeline (Stubs)

**Ziel:** Echter Datenfluss von Bridge bis zur Rückgabe von LR-Settings. Worker-Logik ist noch Stub (keine echten ML-Berechnungen), aber alle Statusübergänge, DB-Writes und Queue-Nachrichten sind real.

### 2.1 Feature Worker

```
consume lrff:jobs:feature
→ lade Preview aus MinIO (s3_key aus Photo-Record)
→ berechne Stub-Features (z.B. 64-dimensionaler Nullvektor)
→ schreibe FeatureVector in DB (pgvector)
→ update Photo.feature_vector_id
→ forward envelope → lrff:jobs:inference
```

### 2.2 Train Worker

```
consume lrff:jobs:train
→ lade alle photo_ids aus dem Payload
→ lade deren FeatureVectors (wenn nicht vorhanden: Job FAILED mit klarer Meldung)
→ Stub: "trainiere" ein Modell (speichere leere JSON-Datei in MinIO)
→ update Profile: model_artifact_key, status → ready
→ Job → completed
```

### 2.3 Inference Worker

```
consume lrff:jobs:inference
→ lade profile_id aus envelope.payload
→ lade Profile (model_artifact_key)
→ lade FeatureVector des Photos
→ Stub: gib base_preset zurück (oder leere Settings)
→ speichere EditResult in DB/MinIO
→ Job → completed, result_key gesetzt
```

### 2.4 EditResult

Neues Konzept — wo landet das Ergebnis?

```
EditResult
├── id            UUID
├── job_id        → Job
├── photo_id      → Photo
├── profile_id    → Profile
├── s3_key        String nullable — vollständige Settings-Datei in MinIO
├── lr_settings   JSONB — kompakte Develop-Settings direkt in DB
│                         (für schnellen Abruf ohne MinIO-Roundtrip)
└── created_at
```

Neuer Endpoint:
- `GET /v1/jobs/{job_id}/result` — gibt `lr_settings` zurück wenn Job completed

### 2.5 Bridge (Tauri — Minimal)

Für Phase 2 reicht ein minimales Tauri-Backend:
- Nimmt Photo-Daten vom LR-Plugin entgegen (lokaler HTTP-Server auf einem Port)
- Ruft `POST /v1/photos` auf
- Ruft `POST /v1/jobs/edit` oder `POST /v1/jobs/train` auf
- Pollt `GET /v1/jobs/{job_id}` bis completed
- Gibt `lr_settings` an LR-Plugin zurück

### 2.6 LR Plugin (Lua — Minimal)

- Export-Dialog: ausgewählte Fotos als JPEG-Preview (1200px längste Seite)
- Schickt Preview + EXIF + aktuelle Develop-Settings an Bridge
- Wartet auf Result (einfaches Polling mit Progress-Dialog)
- Wendet `lr_settings` mit `photo:developSettings` an

**Deliverable:** Foto in LR auswählen → Train-Job starten → Edit-Job starten → LR-Settings werden auf das Foto angewendet. Alles mit Stub-Werten, aber der gesamte Datenfluss funktioniert.

---

## Phase 3 — Echte ML-Pipeline

**Ziel:** Reale Feature-Extraktion, reales Training, reale Inference. Stubs werden durch echte Algorithmen ersetzt — DB-Schema bleibt unverändert.

### 3.1 Feature-Extraktion (`libs/inference-pipeline`)

MVP-Features (kein Deep Learning nötig):
```
- Farbhistogramm RGB + HSL (je 32 bins = 192 Werte)
- Globale Stats: Helligkeit, Kontrast, Sättigung (Mittelwert + Stddev)
- Tonkurven-Charakteristik (Highlights/Shadows/Midtones Verhältnis)
- Schärfe-Schätzung (Laplacian-Varianz)
```
→ ~200-dimensionaler Vektor, schnell zu berechnen, kein GPU-Bedarf

Später als Drop-in: CLIP-Embedding (512/768 dim) — `model_version`-Feld in `FeatureVector` macht das sauber austauschbar.

### 3.2 Training (`libs/` neues Paket: `lr-model-trainer`)

MVP-Modell: **Gradient Boosted Trees** (XGBoost/LightGBM) pro LR-Parameter
```
Input:  FeatureVector (200 dim)
Output: Dict[lr_param_name → float]
        z.B. {"exposure": 0.3, "contrast": 15, "highlights": -20, ...}
```

Pro Profil wird ein Modell trainiert — gespeichert als Pickle/ONNX in MinIO.

Training-Daten: die `lr_develop_settings` der Trainingsfotos sind die Labels.

### 3.3 Inference

```
FeatureVector  →  lade Modell aus MinIO  →  predict LR-Settings
```

Output direkt als `lr_settings` JSONB → kein Umweg.

### 3.4 Qualitätssicherung

- Mean Absolute Error pro LR-Parameter als Trainingsmetrik
- Gespeichert in `Profile.training_metrics` (JSONB, neues Feld)
- Sichtbar im Bridge-UI

**Deliverable:** Echter Lerneffekt — System lernt aus echten LR-Einstellungen und überträgt den Stil auf neue Fotos.

---

## Phase 4 — Production Hardening

**Ziel:** Das System ist zuverlässig, nicht nur funktional. Keine Job-Verluste, keine stuck States, keine Connection-Leaks.

### 4.1 Zuverlässige Queue (At-Least-Once Delivery)

Aktuelles Problem: `BLPOP` entfernt sofort — Worker-Absturz = Job weg.

Lösung mit Redis `LMOVE`:
```
BLMOVE {queue} {queue}:processing RIGHT LEFT (atomisch)
→ verarbeiten
→ LREM {queue}:processing 1 {payload} (Ack)

Recovery-Task (beim Worker-Start + periodisch):
→ scan {queue}:processing
→ Jobs älter als N Minuten → zurück in {queue}
```

### 4.2 Stuck-Job-Recovery

- Worker setzt `started_at` beim Aufnehmen eines Jobs
- Cron-Job (oder Worker-Startup-Check): Jobs mit `status=running` und `started_at < now() - 10min` → zurück auf `queued`, `attempt + 1`
- Nach `max_attempts` (z.B. 3): `failed` mit Reason "max_attempts_exceeded"

### 4.3 Retry-Logik

`attempt`-Feld im Envelope wird endlich genutzt:
```python
MAX_ATTEMPTS = 3
if envelope.attempt >= MAX_ATTEMPTS:
    push_dead_letter(...)
    set_status(FAILED, "max_attempts_exceeded")
else:
    # re-enqueue mit attempt+1 und exponential backoff
```

### 4.4 Connection Management in Workers

Aktuell wird pro Job eine neue Redis/DB-Connection erstellt. Fix:
```python
# main() einmalig:
redis_client = redis_from_env()
publisher = RedisQueuePublisher(redis_client)
session_factory = get_session_factory()

# process_one() nimmt diese als Parameter
```

### 4.5 Redis Persistenz

`docker-compose.yml` Redis ergänzen:
```yaml
redis:
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
```

### 4.6 CI erweitern

- Ruff linting als eigener CI-Job
- API-Endpoint-Tests (pytest + httpx TestClient)
- Worker-Unit-Tests (mock Redis + DB)
- Docker-Build-Check

### 4.7 DB-Trigger für `updated_at`

SQLAlchemy `onupdate` ist unzuverlässig bei direktem SQL. Postgres-Trigger:
```sql
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
-- (analog für photos, profiles)
```

---

## Offene Entscheidungen (bewusst vertagt)

| Thema | Entscheidung nötig bis | Notiz |
|-------|----------------------|-------|
| Auth zwischen Bridge ↔ API | Phase 2 | Shared Secret reicht für MVP |
| SSE vs. Polling für Job-Status | Phase 2 | Polling-Intervall: 2s, SSE als Phase-5-Feature |
| LR Plugin: welche LR-Parameter lernen? | Phase 3 | Initiale Liste festlegen, in `lr_output_keys` |
| Modell-Format: Pickle vs. ONNX | Phase 3 | ONNX bevorzugt (portabler) |
| Multi-User / Auth | Post-MVP | Aktuell: single-user, kein Auth |

---

## Meilensteine

```
Phase 1  ──▶  Alle Tabellen existieren, Contracts aktuell, API hat Photo/Profile-Endpoints
Phase 2  ──▶  Foto in LR → LR-Settings zurück (Stub-Werte, echter Datenfluss)
Phase 3  ──▶  Echter Lerneffekt nachweisbar (MAE < Baseline)
Phase 4  ──▶  Kein Job-Verlust unter simuliertem Worker-Absturz
```

---

## Was wir bewusst NICHT im MVP bauen

- Multi-User / Accounts
- Web-UI (Bridge-Desktop reicht)
- Batch-Optimierungen (viele Fotos parallel)
- Modell-Versionierung mit A/B-Testing
- Cloud-Deployment / Kubernetes
- Deep-Learning-Features (CLIP etc.) — kommt als Drop-in nach Phase 3
