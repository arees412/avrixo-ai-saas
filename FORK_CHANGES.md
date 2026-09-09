# Implemented fork changes

Engineering changes made for Arees Shah / Avrixo Digitals in this derivative:

## Domain and API

- Added `Workspace`, `WorkspaceMember`, `AIWorkflow`, and `AIExecution` tables
  and an Alembic migration extending the original migration chain.
- Added explicit public/request schemas, role checks, tenant-scoped reads,
  member management and owner-controlled admission limits.
- Added workflow creation, full updates, active/disabled state, execution
  submission, paginated history, execution detail, safe provider discovery and
  aggregate database metrics.
- Added a provider protocol, typed result, bounded HTTP response parsing,
  timeout/status sanitization and OpenAI-compatible adapter.
- Added execution orchestration with persisted checkpoints, idempotency keys,
  usage/latency metadata, concurrent/daily admission limits and PostgreSQL row locks.
- Added a composite foreign key preventing workflow/workspace mismatches and
  database constraints for states, roles and numeric limits.
- Prevented account deletion while the account owns a workspace.

## Product interface

- Added dashboard metrics and member identity, workspace list/create/overview,
  workflow list/editor/runner, member controls, governance controls, execution
  history and execution detail using the inherited UI conventions.
- Regenerated the OpenAPI client; added router entries and updated navigation.
- Kept role-denied requests from logging an otherwise authenticated user out.
- Added Avrixo product wordmark text and a shared textarea component.

## Validation and operations

- Added fake-provider backend tests for tenant access, roles, idempotency,
  admission concurrency, persistence, provider errors and response validation.
- Added a login-to-execution Playwright scenario and a separate HTTP test fixture.
- Extended CI with read-only formatting/lint/type/build/client checks, migration
  drift checks, safe environment setup, Compose checks and secret-pattern checks.
- Retained upstream tests and container workflows; adjusted login expectations
  to the new dashboard and made deployments explicitly opt-in.
- Added safe `.env.example` files, a non-overwriting local configuration
  generator, environment ignores and AI environment wiring for Compose.
- Made API import independent of built frontend assets and made inherited
  email-template reads explicitly UTF-8 for Windows reproducibility.
- Added upstream attribution, architecture/development guides and the retained
  upstream README snapshot.

No planned feature is listed here as completed. No inherited code is claimed
as newly authored by Avrixo. No production usage, customers or benchmarks are claimed.
