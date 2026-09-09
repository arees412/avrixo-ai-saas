# Upstream

Original project: **fastapi/full-stack-fastapi-template**

Original repository: https://github.com/fastapi/full-stack-fastapi-template

Base revision: **cb740b656d7a0a6c5e12c7bf8e50343ec94ee9c7**

License: **MIT**, verified from the upstream LICENSE at this revision.

Original copyright: Copyright (c) 2019 Sebastián Ramírez.

This repository is a customized derivative. The inherited architecture, code,
Git history, and implementation remain credited to the original authors and
contributors. The original LICENSE is preserved verbatim. The GitHub fork
relationship is retained. New Avrixo changes are described in [FORK_CHANGES.md](FORK_CHANGES.md).

## Audit of the selected revision

- Default upstream branch: `master`. The fork uses `main` as its review base.
- Python 3.14; FastAPI, Pydantic settings and SQLModel; synchronous database sessions.
- PostgreSQL 18, Alembic migrations, User and Item tables.
- JWT bearer authentication, Argon2 password hashing with bcrypt compatibility,
  registration, account administration, and email password recovery.
- React 19, TypeScript, Vite, TanStack Router/Query, Tailwind CSS and shadcn/ui.
- Bun workspaces and React Email; generated OpenAPI TypeScript client.
- React production assets are served by FastAPI from `backend/app/frontend`.
- Pytest backend suite and Playwright browser suite.
- Docker Compose provides database, Mailpit, application, Adminer and Traefik.
- GitHub Actions cover backend tests/coverage, frontend E2E, pre-commit,
  Compose, workflow security, dependency policy and deployment/release recipes.

The template remains a compatible FastAPI full-stack foundation. Its newer
Bun, Python 3.14 and unified frontend-serving conventions are retained.
See the [original README](docs/upstream/README.md) for historical presentation;
its setup instructions describe upstream, not the customized fork.
