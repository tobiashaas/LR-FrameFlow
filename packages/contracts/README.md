# API- und Daten-Contracts

Dieses Verzeichnis ist die **Kanonical Version** für:

- REST-Schnittstelle zwischen **Bridge** und **FastAPI**: `openapi/bridge-api.yaml`
- JSON-Schemas für payloads und Events: `json-schema/`

## CI Contract-Checks (Empfehlung)

```bash
pip install openapi-spec-validator check-jsonschema
openapi-spec-validator openapi/bridge-api.yaml
check-jsonschema --schemafile json-schema/job-train-request-v1.schema.json examples/job-train-request.example.json
# …weitere Fixtures bei Bedarf
```

Typgenerierung für Bridge oder Python-Client ist optional (`datamodel-codegen`, `openapi-generator-cli`).
