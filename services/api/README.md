Thin FastAPI layer: enqueue jobs (202 Accepted), keine Bildverarbeitung im Request-Pfad.

```bash
cd services/api
python -m venv .venv
.venv\\Scripts\\activate
pip install -e ".[dev]"
uvicorn lr_frameflow_api.main:app --reload
```
