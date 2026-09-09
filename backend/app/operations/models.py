"""Avrixo tenant data. Credentials are deliberately absent from these tables."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(UTC)


class Workspace(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    slug: str = Field(max_length=63, unique=True, index=True)
    owner_id: uuid.UUID = Field(foreign_key="user.id", ondelete="RESTRICT")
    daily_execution_limit: int = Field(default=100, ge=1, le=10000)
    max_concurrent_executions: int = Field(default=3, ge=1, le=20)
    created_at: datetime = Field(
        default_factory=now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    __table_args__ = (
        CheckConstraint(
            "daily_execution_limit BETWEEN 1 AND 10000",
            name="workspace_daily_execution_limit_check",
        ),
        CheckConstraint(
            "max_concurrent_executions BETWEEN 1 AND 20",
            name="workspace_max_concurrent_executions_check",
        ),
    )


class WorkspaceMember(SQLModel, table=True):
    workspace_id: uuid.UUID = Field(
        foreign_key="workspace.id", ondelete="CASCADE", primary_key=True
    )
    user_id: uuid.UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", primary_key=True
    )
    role: str = Field(max_length=10)
    created_at: datetime = Field(
        default_factory=now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'admin', 'member')", name="workspacemember_role_check"
        ),
    )


class AIWorkflow(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(
        foreign_key="workspace.id", ondelete="CASCADE", index=True
    )
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=1000)
    system_prompt: str = Field(max_length=16000)
    provider: str = Field(default="openai-compatible", max_length=40)
    model: str = Field(max_length=120)
    temperature: float = Field(default=0.7)
    max_output_tokens: int = Field(default=1024)
    status: str = Field(default="active", max_length=10)
    created_by: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    created_at: datetime = Field(
        default_factory=now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    __table_args__ = (
        UniqueConstraint("id", "workspace_id"),
        CheckConstraint(
            "status IN ('active', 'disabled')", name="aiworkflow_status_check"
        ),
        CheckConstraint(
            "temperature BETWEEN 0 AND 2", name="aiworkflow_temperature_check"
        ),
        CheckConstraint(
            "max_output_tokens BETWEEN 1 AND 8192",
            name="aiworkflow_max_output_tokens_check",
        ),
    )


class AIExecution(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workflow_id: uuid.UUID = Field(index=True)
    workspace_id: uuid.UUID = Field(
        foreign_key="workspace.id", ondelete="CASCADE", index=True
    )
    input: str
    output: str | None = None
    provider: str = Field(max_length=40)
    model: str = Field(max_length=120)
    status: str = Field(default="pending", max_length=12)
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
    error_message: str | None = Field(default=None, max_length=100)
    idempotency_key: str = Field(max_length=64)
    created_by: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    created_at: datetime = Field(
        default_factory=now,
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    finished_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_id", "workspace_id"],
            ["aiworkflow.id", "aiworkflow.workspace_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("workspace_id", "created_by", "idempotency_key"),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="aiexecution_status_check",
        ),
        CheckConstraint(
            "prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0",
            name="aiexecution_check",
        ),
    )
