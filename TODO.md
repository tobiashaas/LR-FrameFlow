# LRFrameFlow — TODO

This file tracks completed milestones and open work items.
Update it whenever a phase is finished or new tasks are identified.

---

## Completed

### Phase 1 — Domain Foundation
- [x] `ProfileStatus` enum (`draft | training | ready | failed`)
- [x] DB models: `Photo`, `Profile`, `FeatureVector` (pgvector 128-dim), `EditResult`
- [x] Extended `Job` model with `profile_id` FK and `started_at`
- [x] Repositories: `PhotoRepository`, `ProfileRepository`, `FeatureVectorRepository`, `EditResultRepository`
- [x] Migrations 002–006 (photos, profiles, feature_vectors, edit_results, extend jobs)
- [x] API endpoints: `POST /v1/photos`, `GET /v1/profiles`, `GET /v1/profiles/{id}`, `GET /v1/jobs/{id}/result`
- [x] `POST /v1/jobs/edit` now validates profile status (must be `ready`) and photo_ids
- [x] `POST /v1/jobs/train` creates a `Profile` in `DRAFT` status
- [x] OpenAPI spec updated with all new endpoints and schemas
- [x] `photo-upload-v1.schema.json` contract added

### Phase 2 — Real Data Flow (with stubs)
- [x] Feature worker: downloads JPEG from MinIO, skips if vector exists, forwards to inference queue
- [x] Train worker: loads feature vectors + LR settings, saves stub model JSON to MinIO, sets Profile → READY
- [x] Inference worker: loads model artifact from MinIO, creates `EditResult` per photo, sets Job → COMPLETED
- [x] All workers: connection anti-pattern fixed (redis/DB created once in `main()`)
- [x] API: `boto3` + `python-multipart` deps, `storage.py` helper, `get_storage()` dep
- [x] `.env` with port overrides (Postgres 5433, MinIO 9100/9101)

### Phase 3 — Real ML Pipeline
- [x] `extract_features()`: Pillow-based 128-dim histogram (R/G/B/Brightness, 32 bins each)
- [x] `train_model()`: scikit-learn `MultiOutputRegressor(Ridge)` + `StandardScaler`, joblib bytes
- [x] `run_inference()`: deserialize joblib model, predict 10 LR params, zero-model fallback < 3 samples
- [x] Migration 007: vector dim 200 → 128
- [x] All workers use real pipeline functions; inference-pipeline dep added to feature + train workers

---

## Open

### Phase 4 — Production Hardening
- [ ] **At-least-once delivery**: re-enqueue or retry on worker crash before ACK
- [ ] **Stuck job recovery**: cron/daemon to find `running` jobs older than N minutes and reset to `pending`
- [ ] **Redis persistence**: enable AOF or RDB snapshot in compose to survive restarts without message loss
- [ ] **Worker health checks**: expose `/health` or heartbeat for Docker healthcheck
- [ ] **CI linting**: add Ruff lint step to GitHub Actions workflow
- [ ] **CI tests**: add integration tests for API endpoints (pytest + httpx TestClient)
- [ ] **Contracts validation**: extend `validate_contracts.py` to also validate new JSON schemas
- [ ] **Observability**: structured JSON logs, request-id propagation through queue envelopes
- [ ] **Rate limiting / backpressure**: guard API against flooding the queues

### Phase 5 — Bridge & Plugin Integration
- [ ] Tauri bridge app: implement HTTP client to call API (`/v1/photos`, `/v1/jobs/train`, `/v1/jobs/edit`)
- [ ] LR Plugin: trigger export of JPEG preview + metadata to bridge
- [ ] LR Plugin: poll job status and apply returned `lr_settings` back to catalog
- [ ] End-to-end smoke test: LR → Plugin → Bridge → API → Workers → back to LR

### Backlog / Nice-to-have
- [ ] Replace Ridge regression with a gradient boosting model (XGBoost/LightGBM) for better accuracy
- [ ] Add a `GET /v1/jobs` list endpoint with pagination and status filter
- [ ] Profile versioning: bump `version` on retrain instead of overwriting artifact
- [ ] S3 presigned URLs for returning edit result images (not just `lr_settings`)
- [ ] Admin endpoint to manually set Profile status (e.g. force `ready` for testing)
