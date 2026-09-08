"""Execution orchestration; routes do not invoke provider HTTP APIs."""

import logging
import time
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import User
from app.operations.access import membership
from app.operations.models import AIExecution, AIWorkflow, Workspace, now
from app.operations.providers import AIProvider, ProviderError
from app.operations.schemas import ExecuteRequest

logger = logging.getLogger(__name__)


def execute(
    session: Session,
    user: User,
    workflow: AIWorkflow,
    request: ExecuteRequest,
    provider: AIProvider,
) -> AIExecution:
    # Serialize admission per workspace, including across multiple API processes.
    workspace = session.exec(
        select(Workspace).where(Workspace.id == workflow.workspace_id).with_for_update()
    ).one()
    membership(session, user, workspace.id)
    existing = session.exec(
        select(AIExecution).where(
            AIExecution.workspace_id == workspace.id,
            AIExecution.created_by == user.id,
            AIExecution.idempotency_key == request.idempotency_key,
        )
    ).first()
    if existing:
        if existing.workflow_id != workflow.id or existing.input != request.input:
            raise HTTPException(409, "Idempotency key already used for another request")
        session.commit()
        return existing
    session.refresh(workflow)
    if workflow.status != "active":
        raise HTTPException(409, "Workflow is disabled")
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    used = session.exec(
        select(func.count())
        .select_from(AIExecution)
        .where(
            AIExecution.workspace_id == workspace.id, AIExecution.created_at >= today
        )
    ).one()
    active = session.exec(
        select(func.count())
        .select_from(AIExecution)
        .where(
            AIExecution.workspace_id == workspace.id,
            col(AIExecution.status).in_(["pending", "running"]),
        )
    ).one()
    if (
        used >= workspace.daily_execution_limit
        or active >= workspace.max_concurrent_executions
    ):
        raise HTTPException(429, "Workspace execution limit reached")
    execution = AIExecution(
        workflow_id=workflow.id,
        workspace_id=workspace.id,
        input=request.input,
        provider=workflow.provider,
        model=workflow.model,
        created_by=user.id,
        idempotency_key=request.idempotency_key,
    )
    # Snapshot configuration before releasing the lock, so edits cannot alter an admitted run.
    model, system_prompt, temperature, max_output_tokens = (
        workflow.model,
        workflow.system_prompt,
        workflow.temperature,
        workflow.max_output_tokens,
    )
    session.add(execution)
    session.commit()
    execution.status = "running"
    session.add(execution)
    session.commit()
    started = time.perf_counter()
    try:
        result = provider.generate(
            model=model,
            system_prompt=system_prompt,
            prompt=request.input,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        execution.output = result.output
        execution.prompt_tokens = result.prompt_tokens
        execution.completion_tokens = result.completion_tokens
        execution.total_tokens = result.total_tokens
        execution.status = "completed"
    except ProviderError as exc:
        execution.status = "failed"
        allowed = {
            "provider_not_configured",
            "provider_timeout",
            "provider_unavailable",
            "provider_invalid_response",
            "provider_response_too_large",
        }
        execution.error_message = str(exc) if str(exc) in allowed else "provider_failed"
    except Exception:
        # No raw exception, prompt, response body, or credential is logged.
        execution.status = "failed"
        execution.error_message = "provider_failed"
    execution.latency_ms = max(0, round((time.perf_counter() - started) * 1000))
    execution.finished_at = now()
    session.add(execution)
    session.commit()
    session.refresh(execution)
    logger.info(
        "ai_execution id=%s workspace=%s status=%s latency_ms=%s",
        execution.id,
        execution.workspace_id,
        execution.status,
        execution.latency_ms,
    )
    return execution
