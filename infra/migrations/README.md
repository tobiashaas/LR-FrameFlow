# Datenbank-Migrationen (Alembic)

Aus dem Repo-Root oder diesem Ordner:

```bash
set DATABASE_URL=postgresql+psycopg://lrframeflow:lrframeflow@127.0.0.1:5432/lrframeflow
cd infra/migrations
pip install -e ../../libs/domain -e ../../libs/persistence alembic
alembic upgrade head
```

`prepend_sys_path` in `alembic.ini` nimmt den Monorepo-Root auf, damit `lr_frameflow_persistence` importierbar ist.
