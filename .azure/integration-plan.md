# Integration handoff

## Backend
- Project folder: .
- Run command: `python backend/app.py`
- App port: 5000
- Health endpoint: `GET /api/health`
- Smoke test command: `python verify_app.py`
- Code validation: `python -m compileall backend`

## Frontend
- Frontend type: server-rendered Flask templates with static assets
- UI folder: `templates/` + `static/`
- Build/dev command: not applicable; no separate Vite/React project
- API seam to swap: not applicable; templates render server-side views directly
- Mock files to delete: none; this app is not using a mock-data frontend layer

## API routes
- `GET /`
- `GET /login`, `POST /login`
- `GET /logout`
- `GET /dashboard`
- `GET /patients`, `GET /patients/new`, `POST /patients/new`, `GET /patients/<id>`, `GET /patients/<id>/edit`, `POST /patients/<id>/edit`, `POST /patients/<id>/delete`
- `GET /appointments`, `GET /appointments/new`, `POST /appointments/new`, `GET /appointments/<id>/edit`, `POST /appointments/<id>/edit`, `POST /appointments/<id>/cancel`
- `GET /assessments`, `GET /assessments/new`, `POST /assessments/new`, `GET /assessments/<id>`, `GET /assessments/<id>/pdf`
- `GET /treatments`, `GET /treatments/new`, `POST /treatments/new`, `GET /treatments/<id>/edit`, `POST /treatments/<id>/edit`
- `GET /packages`, `GET /packages/new`, `POST /packages/new`, `GET /packages/<id>/edit`, `POST /packages/<id>/edit`
- `GET /billing`, `GET /billing/new`, `POST /billing/new`, `GET /payments`, `GET /invoices/<id>`
- `GET /staff`, `GET /staff/new`, `POST /staff/new`, `GET /staff/add`, `POST /staff/add`, `GET /staff/<id>/edit`, `POST /staff/<id>/edit`, `GET /staff/<id>/permissions`, `POST /staff/<id>/permissions`
- `GET /reports`, `GET /audit-logs`, `GET /backup`
- `GET /api/health`

## Database
- Type: SQLite (default local database)
- Model layer: SQLAlchemy via `backend/models.py`
- Migration/tooling: startup creates schema via `db.create_all()` and applies schema patching in `ensure_database_schema()`
- Connection env var: `DATABASE_URL`
- Default local value: `sqlite:///ree_forma.db`
- No seed data required; if no admin record exists, one is created automatically with username `admin` and password `admin123`

## Shared types and services
- Shared types: none; app uses server-rendered templates and SQLAlchemy models
- Essential services:
  - Local database persistence
  - Login/session-based access control
  - Assessment PDF generation via ReportLab
  - Backup/export workflow for SQLite database
- Enhancement services:
  - WhatsApp integration (`WHATSAPP_*` environment settings, disabled by default)

## Verification status
- Health smoke test passed: `python verify_app.py` returned `status 200` and `login_status 200`
- Do not seed the database beyond the app’s built-in admin bootstrap logic
