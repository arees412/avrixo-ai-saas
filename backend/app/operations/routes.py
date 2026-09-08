import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models import Message, User
from app.operations.access import (
    membership,
    require_manager,
    workflow_for_user,
    workspace_public,
)
from app.operations.models import (
    AIExecution,
    AIWorkflow,
    Workspace,
    WorkspaceMember,
    now,
)
from app.operations.providers import AIProvider, get_provider
from app.operations.schemas import (
    ExecuteRequest,
    ExecutionPublic,
    GovernanceUpdate,
    MemberPublic,
    MemberWrite,
    Metrics,
    ProviderPublic,
    WorkflowPublic,
    WorkflowWrite,
    WorkspaceCreate,
    WorkspacePublic,
)
from app.operations.service import execute

router = APIRouter(tags=["operations"])
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
ProviderDep = Annotated[AIProvider, Depends(get_provider)]


@router.post("/workspaces", response_model=WorkspacePublic, status_code=201)
def create_workspace(
    session: SessionDep, current_user: CurrentUser, body: WorkspaceCreate
) -> WorkspacePublic:
    workspace = Workspace(**body.model_dump(), owner_id=current_user.id)
    session.add(workspace)
    try:
        session.flush()
        member = WorkspaceMember(
            workspace_id=workspace.id, user_id=current_user.id, role="owner"
        )
        session.add(member)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Workspace slug is unavailable") from None
    return workspace_public(workspace, member)


@router.get("/workspaces", response_model=list[WorkspacePublic])
def list_workspaces(
    session: SessionDep,
    current_user: CurrentUser,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[WorkspacePublic]:
    rows = session.exec(
        select(Workspace, WorkspaceMember)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == current_user.id)
        .order_by(col(Workspace.created_at), col(Workspace.id))
        .offset(offset)
        .limit(limit)
    ).all()
    return [workspace_public(w, m) for w, m in rows]


@router.get("/workspaces/{workspace_id}", response_model=WorkspacePublic)
def read_workspace(
    workspace_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> WorkspacePublic:
    member = membership(session, current_user, workspace_id)
    workspace = session.get(Workspace, workspace_id)
    assert workspace is not None
    return workspace_public(workspace, member)


@router.patch("/workspaces/{workspace_id}/governance", response_model=WorkspacePublic)
def update_governance(
    workspace_id: uuid.UUID,
    body: GovernanceUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> WorkspacePublic:
    member = membership(session, current_user, workspace_id)
    if member.role != "owner":
        raise HTTPException(403, "Workspace owner role required")
    workspace = session.exec(
        select(Workspace).where(Workspace.id == workspace_id).with_for_update()
    ).one()
    workspace.sqlmodel_update(body.model_dump())
    workspace.updated_at = now()
    session.add(workspace)
    session.commit()
    return workspace_public(workspace, member)


@router.get("/workspaces/{workspace_id}/members", response_model=list[MemberPublic])
def list_members(
    workspace_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[MemberPublic]:
    membership(session, current_user, workspace_id)
    members = session.exec(
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(col(WorkspaceMember.created_at), col(WorkspaceMember.user_id))
        .offset(offset)
        .limit(limit)
    ).all()
    return [MemberPublic.model_validate(m) for m in members]


@router.put("/workspaces/{workspace_id}/members", response_model=MemberPublic)
def set_member(
    workspace_id: uuid.UUID,
    body: MemberWrite,
    session: SessionDep,
    current_user: CurrentUser,
) -> WorkspaceMember:
    actor = membership(session, current_user, workspace_id)
    require_manager(actor)
    session.exec(
        select(Workspace).where(Workspace.id == workspace_id).with_for_update()
    ).one()
    actor = membership(session, current_user, workspace_id)
    require_manager(actor)
    target = session.get(WorkspaceMember, (workspace_id, body.user_id))
    if (target and target.role == "owner") or (
        actor.role != "owner"
        and (body.role != "member" or (target and target.role != "member"))
    ):
        raise HTTPException(
            403, "Only owners can manage admin roles; ownership is immutable"
        )
    user = session.get(User, body.user_id)
    if not user or not user.is_active:
        raise HTTPException(404, "Active user not found")
    if target is None:
        target = WorkspaceMember(
            workspace_id=workspace_id, user_id=body.user_id, role=body.role
        )
    else:
        target.role = body.role
    session.add(target)
    session.commit()
    return target


@router.delete("/workspaces/{workspace_id}/members/{user_id}", response_model=Message)
def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Message:
    actor = membership(session, current_user, workspace_id)
    require_manager(actor)
    session.exec(
        select(Workspace).where(Workspace.id == workspace_id).with_for_update()
    ).one()
    actor = membership(session, current_user, workspace_id)
    require_manager(actor)
    target = session.get(WorkspaceMember, (workspace_id, user_id))
    if not target:
        raise HTTPException(404, "Member not found")
    if target.role == "owner" or (actor.role != "owner" and target.role != "member"):
        raise HTTPException(403, "Cannot remove this role")
    session.delete(target)
    session.commit()
    return Message(message="Member removed")


@router.post(
    "/workspaces/{workspace_id}/workflows",
    response_model=WorkflowPublic,
    status_code=201,
)
def create_workflow(
    workspace_id: uuid.UUID,
    body: WorkflowWrite,
    session: SessionDep,
    current_user: CurrentUser,
) -> AIWorkflow:
    require_manager(membership(session, current_user, workspace_id))
    workflow = AIWorkflow(
        **body.model_dump(), workspace_id=workspace_id, created_by=current_user.id
    )
    session.add(workflow)
    session.commit()
    return workflow


@router.get("/workspaces/{workspace_id}/workflows", response_model=list[WorkflowPublic])
def list_workflows(
    workspace_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[WorkflowPublic]:
    membership(session, current_user, workspace_id)
    workflows = session.exec(
        select(AIWorkflow)
        .where(AIWorkflow.workspace_id == workspace_id)
        .order_by(col(AIWorkflow.created_at), col(AIWorkflow.id))
        .offset(offset)
        .limit(limit)
    ).all()
    return [WorkflowPublic.model_validate(w) for w in workflows]


@router.get("/workflows/{workflow_id}", response_model=WorkflowPublic)
def read_workflow(
    workflow_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> AIWorkflow:
    return workflow_for_user(session, current_user, workflow_id)


@router.put("/workflows/{workflow_id}", response_model=WorkflowPublic)
def update_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowWrite,
    session: SessionDep,
    current_user: CurrentUser,
) -> AIWorkflow:
    workflow = workflow_for_user(session, current_user, workflow_id)
    require_manager(membership(session, current_user, workflow.workspace_id))
    workflow.sqlmodel_update(body.model_dump())
    workflow.updated_at = now()
    session.add(workflow)
    session.commit()
    return workflow


@router.post("/workflows/{workflow_id}/execute", response_model=ExecutionPublic)
def execute_workflow(
    workflow_id: uuid.UUID,
    body: ExecuteRequest,
    session: SessionDep,
    current_user: CurrentUser,
    provider: ProviderDep,
) -> AIExecution:
    workflow = workflow_for_user(session, current_user, workflow_id)
    return execute(session, current_user, workflow, body, provider)


@router.get(
    "/workspaces/{workspace_id}/executions", response_model=list[ExecutionPublic]
)
def list_executions(
    workspace_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    limit: Limit = 25,
    offset: Offset = 0,
) -> list[ExecutionPublic]:
    membership(session, current_user, workspace_id)
    executions = session.exec(
        select(AIExecution)
        .where(AIExecution.workspace_id == workspace_id)
        .order_by(col(AIExecution.created_at).desc(), col(AIExecution.id))
        .offset(offset)
        .limit(limit)
    ).all()
    return [ExecutionPublic.model_validate(e) for e in executions]


@router.get("/executions/{execution_id}", response_model=ExecutionPublic)
def read_execution(
    execution_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> AIExecution:
    execution = session.get(AIExecution, execution_id)
    if execution is None:
        raise HTTPException(404, "Execution not found")
    membership(session, current_user, execution.workspace_id)
    return execution


@router.get("/operations/metrics", response_model=Metrics)
def metrics(
    session: SessionDep,
    current_user: CurrentUser,
    workspace_id: uuid.UUID | None = None,
) -> Metrics:
    if workspace_id:
        membership(session, current_user, workspace_id)
    scope = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == current_user.id
    )
    if workspace_id:
        scope = scope.where(WorkspaceMember.workspace_id == workspace_id)
    base = (
        select(func.count())
        .select_from(AIExecution)
        .where(col(AIExecution.workspace_id).in_(scope))
    )
    return Metrics(
        workspaces=session.exec(
            select(func.count())
            .select_from(Workspace)
            .where(col(Workspace.id).in_(scope))
        ).one(),
        workflows=session.exec(
            select(func.count())
            .select_from(AIWorkflow)
            .where(col(AIWorkflow.workspace_id).in_(scope))
        ).one(),
        executions=session.exec(base).one(),
        successful_executions=session.exec(
            base.where(AIExecution.status == "completed")
        ).one(),
        failed_executions=session.exec(
            base.where(AIExecution.status == "failed")
        ).one(),
        total_tokens=int(
            session.exec(
                select(func.coalesce(func.sum(AIExecution.total_tokens), 0)).where(
                    col(AIExecution.workspace_id).in_(scope)
                )
            ).one()
            or 0
        ),
        executions_with_usage=session.exec(
            base.where(col(AIExecution.total_tokens).is_not(None))
        ).one(),
    )


@router.get("/operations/providers", response_model=list[ProviderPublic])
def providers(current_user: CurrentUser) -> list[ProviderPublic]:
    del current_user
    return [
        ProviderPublic(
            configured=bool(settings.AI_BASE_URL and settings.AI_API_KEY),
            default_model=settings.AI_DEFAULT_MODEL,
        )
    ]
