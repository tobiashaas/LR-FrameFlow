# API- und Daten-Contracts

Dieses Verzeichnis ist die **Kanonical Version** für:

- REST-Schnittstelle zwischen **Bridge** und **FastAPI**: `openapi/bridge-api.yaml`
- JSON-Schemas für payloads, Envelopes und Events: `json-schema/` (insb. **`job-envelope-v1`** für Redis)

## CI Contract-Checks (Empfehlung)

```bash
pip install openapi-spec-validator check-jsonschema
openapi-spec-validator openapi/bridge-api.yaml
check-jsonschema --schemafile json-schema/job-train-request-v1.schema.json examples/job-train-request.example.json
check-jsonschema --schemafile json-schema/job-envelope-v1.schema.json examples/job-envelope.example.json
```

Automatisch: Root-Skript `python scripts/validate_contracts.py` oder Workflow `.github/workflows/ci.yml`.

Typgenerierung für Bridge oder Python-Client ist optional (`datamodel-codegen`, `openapi-generator-cli`).
