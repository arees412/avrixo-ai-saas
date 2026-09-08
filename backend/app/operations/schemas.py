import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["owner", "admin", "member"]


class Schema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, extra="forbid", str_strip_whitespace=True
    )


class WorkspaceCreate(Schema):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(
        min_length=3, max_length=63, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )


class WorkspacePublic(WorkspaceCreate):
    id: uuid.UUID
    owner_id: uuid.UUID
    daily_execution_limit: int
    max_concurrent_executions: int
    created_at: datetime
    updated_at: datetime
    role: Role


class GovernanceUpdate(Schema):
    daily_execution_limit: int = Field(ge=1, le=10000)
    max_concurrent_executions: int = Field(ge=1, le=20)


class MemberWrite(Schema):
    user_id: uuid.UUID
    role: Literal["admin", "member"] = "member"


class MemberPublic(Schema):
    user_id: uuid.UUID
    role: Role
    created_at: datetime


class WorkflowWrite(Schema):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    system_prompt: str = Field(min_length=1, max_length=16000)
    provider: Literal["openai-compatible"] = "openai-compatible"
    model: str = Field(
        min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]*$"
    )
    temperature: float = Field(default=0.7, ge=0, le=2, allow_inf_nan=False)
    max_output_tokens: int = Field(default=1024, ge=1, le=8192)
    status: Literal["active", "disabled"] = "active"


class WorkflowPublic(WorkflowWrite):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ExecuteRequest(Schema):
    input: str = Field(min_length=1, max_length=32000)
    idempotency_key: str = Field(
        min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"
    )


class ExecutionPublic(Schema):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    input: str
    output: str | None
    provider: str
    model: str
    status: Literal["pending", "running", "completed", "failed"]
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: int | None
    error_message: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    finished_at: datetime | None


class Metrics(Schema):
    workspaces: int
    workflows: int
    executions: int
    successful_executions: int
    failed_executions: int
    total_tokens: int
    executions_with_usage: int


class ProviderPublic(Schema):
    id: str = "openai-compatible"
    configured: bool
    default_model: str
