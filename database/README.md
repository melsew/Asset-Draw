# Database

PostgreSQL is the transactional source of truth. SQLAlchemy 2 models are under `backend/app/*/models.py`; Alembic
creates the full schema from an empty PostgreSQL 16 database and applies T1–T9 triggers and the database roles.
The Mermaid ER diagram is generated from model metadata at `docs/design/er-diagram.md` with:

```powershell
python scripts/generate_er_diagram.py
```

Apply the schema with `cd backend; alembic upgrade head` after setting `DATABASE_URL`.

The database invariant tests use a separate `TEST_DATABASE_URL`. It must point to a disposable PostgreSQL
database whose name contains `test`; the fixture runs `alembic upgrade head` against it. Do not point this
variable at a database containing data that must be retained.

Migration-created group roles are `app_api`, `app_worker`, `app_migrator`, and `app_readonly_audit`. They are
created with `NOLOGIN`; deployment-specific login roles and membership grants are not configured by this MVP
schema.
