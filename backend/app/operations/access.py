import uuid
from typing import cast

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import User
from app.operations.models import AIWorkflow, Workspace, WorkspaceMember
from app.operations.schemas import Role, WorkspacePublic


def membership(
    session: Session, user: User, workspace_id: uuid.UUID
) -> WorkspaceMember:
    member = session.exec(
        select(WorkspaceMember)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
        .execution_options(populate_existing=True)
    ).first()
    if member is None:
        # Identical response for missing tenants and tenants the caller cannot see.
        raise HTTPException(404, "Workspace not found")
    return member


def require_manager(member: WorkspaceMember) -> None:
    if member.role not in {"owner", "admin"}:
        raise HTTPException(403, "Workspace manager role required")


def workflow_for_user(
    session: Session, user: User, workflow_id: uuid.UUID
) -> AIWorkflow:
    workflow = session.get(AIWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(404, "Workflow not found")
    membership(session, user, workflow.workspace_id)
    return workflow


def workspace_public(workspace: Workspace, member: WorkspaceMember) -> WorkspacePublic:
    return WorkspacePublic(
        **{
            key: getattr(workspace, key)
            for key in WorkspacePublic.model_fields
            if key != "role"
        },
        role=cast(Role, member.role),
    )
