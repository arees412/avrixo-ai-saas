# Development

## Prerequisites

- Python 3.14 (see `.python-version`) and uv.
- Bun 1.3.12, Docker with Compose v2, Git.
- Ports 5432/1025/8025 for PostgreSQL/Mailpit, 8000 for the API and 5173 for Vite.

The repository is a Bun workspace and a uv workspace. Keep `bun.lock` and
`uv.lock`; install frozen dependencies instead of regenerating them casually.

## Configuration and local startup

From the repository root:

```bash
python scripts/setup_env.py
docker compose up -d --wait db mailpit
uv sync --frozen --all-packages
bun ci
cd backend
uv run alembic upgrade head
uv run python -m app.initial_data
uv run fastapi dev
```

`setup_env.py` refuses to overwrite `.env` and substitutes random local
credentials into `.env.example`. Read your generated file for the initial
administrator password. `.env` is never intended for version control.

In another shell from the root:

```bash
cp frontend/.env.example frontend/.env
bun run dev
```

In PowerShell use `Copy-Item frontend/.env.example frontend/.env`. The other
commands work as written. The UI is http://localhost:5173, API docs are
http://localhost:8000/docs, and Mailpit is http://localhost:8025.

## AI provider configuration

Set these server-only values in the root `.env`, then restart FastAPI:

| Variable | Purpose |
| --- | --- |
| `AI_BASE_URL` | Operator-approved HTTPS API base ending in `/v1` where appropriate |
| `AI_API_KEY` | Provider credential; never expose through a `VITE_` variable |
| `AI_DEFAULT_MODEL` | A model hint for the workflow editor |
| `AI_TIMEOUT_SECONDS` | HTTP timeout, 1–120 seconds; default 45 |

The endpoint must support `POST chat/completions` with messages, model,
temperature, `max_tokens`, and non-streaming content. Workspaces select model,
instructions, temperature and output token limit. Blank provider configuration
is allowed during setup; an attempted execution records `provider_not_configured`.
No real AI key is required for automated tests.

## Migrations

```bash
cd backend
uv run alembic upgrade head
uv run alembic check
```

When intentionally changing a model, create and review a new migration:

```bash
uv run alembic revision --autogenerate -m "Describe schema change"
```

Do not replace upstream revisions. The Avrixo migration follows
`fe56fa70289e`. Test upgrades/downgrades only against disposable databases;
downgrading the Avrixo migration removes workspace/workflow/execution data.

## Backend checks

Use a disposable PostgreSQL database. The inherited suite deletes its test
records at teardown. **Never point these tests at a production database.**

```bash
cd backend
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
uv run ty check app
uv run coverage run -m pytest tests
uv run coverage report --fail-under=90
```

Run only fork tests with `uv run pytest tests/api/routes/test_operations.py`.
They use real PostgreSQL constraints/row locks and injected fake providers.
Adapter tests use httpx mock transports, not network or paid calls.

## Generated client and frontend checks

From the repository root, with `.env` prepared:

```bash
cd backend
uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > ../frontend/openapi.json
cd ../frontend
bun run generate-client
bun run lint:check
bun run build
```

For Windows PowerShell 5, write the schema with Python using UTF-8 rather than
shell redirection (which may emit UTF-16):

```powershell
uv run python -c "import json; from pathlib import Path; from app.main import app; Path('../frontend/openapi.json').write_text(json.dumps(app.openapi()), encoding='utf-8')"
```

The generated client lives in `frontend/src/client`. Do not hand-edit it.
Vite generates `routeTree.gen.ts`. API imports also work before the frontend
is built. The production build goes to `backend/app/frontend` and uses the
same origin when `VITE_API_URL` is empty.

## Docker and browser tests

Normal application startup:

```bash
docker compose config --quiet
docker compose run --rm backend bash scripts/prestart.sh
docker compose up --build -d backend
```

Open http://localhost:8000. The upstream `compose.override.yml` is development
only; use `compose.yml` plus `compose.deploy.yml` for a separately reviewed
self-hosted deployment. Set `DOMAIN`, secrets, HTTPS and operational controls
before doing so. GitHub deployment recipes are opt-in via `ENABLE_DEPLOYMENT`.

Full E2E with the explicit test-only provider overlay:

```bash
docker compose -f compose.yml -f compose.override.yml -f compose.test.yml build
docker compose -f compose.yml -f compose.override.yml -f compose.test.yml run --rm backend bash scripts/prestart.sh
docker compose -f compose.yml -f compose.override.yml -f compose.test.yml run --rm playwright bunx playwright test
```

Use an isolated Compose project/database for this flow. Test workflows use
`test-model`; the fixture returns a clearly marked test output and deterministic
usage. It is absent from the application import path and normal deployment.
The new E2E logs in, creates a workspace/workflow, invokes the real API and
adapter against the fixture, and checks persisted output/history in the UI.

## CI and provenance

Static validation checks Python/TypeScript, generated SDK consistency,
formatting, secret patterns and Compose. Backend CI runs real PostgreSQL
migrations/tests with at least 90% coverage. Existing Compose and Playwright
workflows are retained. No pipeline uses a real paid AI provider.

`UPSTREAM.md` records the immutable base; `FORK_CHANGES.md` records only
implemented changes. Keep the MIT copyright and fork relationship intact.
