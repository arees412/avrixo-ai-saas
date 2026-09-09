import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.models import User
from app.operations.models import AIExecution, Workspace, WorkspaceMember
from app.operations.providers import (
    Generation,
    OpenAICompatibleProvider,
    ProviderError,
    get_provider,
)

PREFIX = "/api/v1"
WORKFLOW = {
    "name": "Support brief",
    "system_prompt": "Summarize the request in two bullets.",
    "model": "test-model",
}


class FakeProvider:
    calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        assert kwargs["model"] == "test-model"
        return Generation(
            output="A useful summary",
            prompt_tokens=12,
            completion_tokens=8,
            total_tokens=20,
        )

    def health_check(self):
        return True


@pytest.fixture
def tenant(client: TestClient, db: Session):
    users = []
    headers = []
    for index in range(3):
        user = User(
            email=f"{uuid.uuid4()}@example.com",
            hashed_password="unused-test-hash",
            is_superuser=index == 2,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        users.append(user)
        token = create_access_token(user.id, timedelta(minutes=5))
        headers.append({"Authorization": f"Bearer {token}"})
    fake = FakeProvider()
    app.dependency_overrides[get_provider] = lambda: fake
    response = client.post(
        f"{PREFIX}/workspaces",
        headers=headers[0],
        json={"name": "Team", "slug": f"team-{uuid.uuid4().hex}"},
    )
    assert response.status_code == 201, response.text
    workspace = response.json()
    yield workspace, users, headers, fake
    app.dependency_overrides.pop(get_provider, None)
    db.rollback()
    for w in db.exec(
        select(Workspace).where(Workspace.owner_id.in_([u.id for u in users]))
    ).all():
        db.delete(w)
    db.commit()
    for user in users:
        db.delete(user)
    db.commit()


def workflow(client, tenant):
    w, _, headers, _ = tenant
    response = client.post(
        f"{PREFIX}/workspaces/{w['id']}/workflows", headers=headers[0], json=WORKFLOW
    )
    assert response.status_code == 201, response.text
    return response.json()


def run(client, flow, headers, key="request-1"):
    return client.post(
        f"{PREFIX}/workflows/{flow['id']}/execute",
        headers=headers,
        json={"input": "Please organize this request", "idempotency_key": key},
    )


def test_workspace_creation_and_validation(client, db, tenant):
    w, users, headers, _ = tenant
    assert w["role"] == "owner"
    assert db.get(WorkspaceMember, (uuid.UUID(w["id"]), users[0].id)).role == "owner"
    assert (
        client.post(
            f"{PREFIX}/workspaces", json={"name": "No auth", "slug": "no-auth"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"{PREFIX}/workspaces",
            headers=headers[0],
            json={"name": "Duplicate", "slug": w["slug"]},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{PREFIX}/workspaces",
            headers=headers[0],
            json={"name": " ", "slug": "bad slug"},
        ).status_code
        == 422
    )
    assert (
        client.get(f"{PREFIX}/workspaces?limit=101", headers=headers[0]).status_code
        == 422
    )
    assert client.get(f"{PREFIX}/workspaces", headers=headers[1]).json() == []


@pytest.mark.parametrize("outsider", [1, 2])
def test_cross_tenant_access_including_platform_admin(client, tenant, outsider):
    w, _, headers, fake = tenant
    flow = workflow(client, tenant)
    execution = run(client, flow, headers[0]).json()
    for path in [
        f"workspaces/{w['id']}",
        f"workspaces/{w['id']}/workflows",
        f"workspaces/{w['id']}/executions",
        f"workspaces/{w['id']}/members",
        f"workflows/{flow['id']}",
        f"executions/{execution['id']}",
        f"operations/metrics?workspace_id={w['id']}",
    ]:
        assert (
            client.get(f"{PREFIX}/{path}", headers=headers[outsider]).status_code == 404
        )
    assert run(client, flow, headers[outsider]).status_code == 404
    assert (
        client.put(
            f"{PREFIX}/workflows/{flow['id']}", headers=headers[outsider], json=WORKFLOW
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"{PREFIX}/workspaces/{w['id']}/workflows",
            headers=headers[outsider],
            json=WORKFLOW,
        ).status_code
        == 404
    )
    assert (
        client.get(f"{PREFIX}/operations/metrics", headers=headers[outsider]).json()[
            "executions"
        ]
        == 0
    )
    assert fake.calls == 1


def test_member_roles_and_revocation(client, tenant):
    w, users, headers, _ = tenant
    path = f"{PREFIX}/workspaces/{w['id']}/members"
    assert (
        client.put(
            path,
            headers=headers[0],
            json={"user_id": str(users[1].id), "role": "member"},
        ).status_code
        == 200
    )
    assert (
        client.get(f"{PREFIX}/workspaces/{w['id']}", headers=headers[1]).json()["role"]
        == "member"
    )
    flow = workflow(client, tenant)
    assert run(client, flow, headers[1]).json()["status"] == "completed"
    assert (
        client.post(
            f"{PREFIX}/workspaces/{w['id']}/workflows",
            headers=headers[1],
            json=WORKFLOW,
        ).status_code
        == 403
    )
    assert (
        client.put(
            path,
            headers=headers[1],
            json={"user_id": str(users[1].id), "role": "admin"},
        ).status_code
        == 403
    )
    assert (
        client.put(
            path,
            headers=headers[0],
            json={"user_id": str(users[1].id), "role": "admin"},
        ).status_code
        == 200
    )
    assert (
        client.put(
            path,
            headers=headers[1],
            json={"user_id": str(users[2].id), "role": "admin"},
        ).status_code
        == 403
    )
    assert (
        client.put(
            path,
            headers=headers[1],
            json={"user_id": str(users[2].id), "role": "member"},
        ).status_code
        == 200
    )
    assert client.delete(f"{path}/{users[0].id}", headers=headers[0]).status_code == 403
    assert client.delete(f"{path}/{users[1].id}", headers=headers[0]).status_code == 200
    assert run(client, flow, headers[1], "revoked").status_code == 404


def test_success_metadata_idempotency_and_metrics(client, db, tenant):
    w, _, headers, fake = tenant
    flow = workflow(client, tenant)
    response = run(client, flow, headers[0])
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "completed"
    assert result["total_tokens"] == 20
    assert result["prompt_tokens"] == 12 and result["completion_tokens"] == 8
    assert result["latency_ms"] >= 0 and result["finished_at"]
    assert result["provider"] == "openai-compatible" and result["model"] == "test-model"
    assert db.get(AIExecution, uuid.UUID(result["id"])).output == "A useful summary"
    assert run(client, flow, headers[0]).json()["id"] == result["id"]
    assert fake.calls == 1
    collision = client.post(
        f"{PREFIX}/workflows/{flow['id']}/execute",
        headers=headers[0],
        json={"input": "Changed", "idempotency_key": "request-1"},
    )
    assert collision.status_code == 409
    assert (
        client.get(
            f"{PREFIX}/workspaces/{w['id']}/executions", headers=headers[0]
        ).json()[0]["id"]
        == result["id"]
    )
    stats = client.get(
        f"{PREFIX}/operations/metrics?workspace_id={w['id']}", headers=headers[0]
    ).json()
    assert stats == {
        "workspaces": 1,
        "workflows": 1,
        "executions": 1,
        "successful_executions": 1,
        "failed_executions": 0,
        "total_tokens": 20,
        "executions_with_usage": 1,
    }


@pytest.mark.parametrize(
    "error",
    [ProviderError("provider_timeout"), RuntimeError("sensitive-provider-body-secret")],
)
def test_provider_failure_is_persisted_and_sanitized(client, db, tenant, error, caplog):
    _, _, headers, fake = tenant

    def fail(**_kwargs):
        raise error

    fake.generate = fail
    response = run(client, workflow(client, tenant), headers[0])
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "failed" and result["output"] is None
    assert result["total_tokens"] is None
    assert result["error_message"] in {"provider_timeout", "provider_failed"}
    assert "sensitive-provider-body-secret" not in response.text + caplog.text
    assert db.get(AIExecution, uuid.UUID(result["id"])).status == "failed"


def test_disabled_workflow_and_daily_governance(client, tenant):
    w, _, headers, fake = tenant
    flow = workflow(client, tenant)
    client.put(
        f"{PREFIX}/workflows/{flow['id']}",
        headers=headers[0],
        json={**WORKFLOW, "status": "disabled"},
    )
    assert run(client, flow, headers[0]).status_code == 409
    client.put(f"{PREFIX}/workflows/{flow['id']}", headers=headers[0], json=WORKFLOW)
    assert (
        client.patch(
            f"{PREFIX}/workspaces/{w['id']}/governance",
            headers=headers[0],
            json={"daily_execution_limit": 1, "max_concurrent_executions": 1},
        ).status_code
        == 200
    )
    assert run(client, flow, headers[0]).status_code == 200
    assert run(client, flow, headers[0], "second").status_code == 429
    assert run(client, flow, headers[0]).status_code == 200
    assert fake.calls == 1


def test_concurrent_admission_and_inflight_replay(client, tenant):
    w, _, headers, fake = tenant
    flow = workflow(client, tenant)
    client.patch(
        f"{PREFIX}/workspaces/{w['id']}/governance",
        headers=headers[0],
        json={"daily_execution_limit": 100, "max_concurrent_executions": 1},
    )
    entered, release = Event(), Event()

    def slow(**_kwargs):
        entered.set()
        assert release.wait(10)
        return Generation(output="done")

    fake.generate = slow
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(run, client, flow, headers[0])
        try:
            assert entered.wait(10)
            assert run(client, flow, headers[0], "other").status_code == 429
            replay = run(client, flow, headers[0]).json()
            assert replay["status"] == "running"
        finally:
            release.set()
        assert first.result().json()["status"] == "completed"


def test_database_prevents_mismatched_workflow_tenant(client, db, tenant):
    w, users, _, _ = tenant
    flow = workflow(client, tenant)
    other = Workspace(name="Other", slug=uuid.uuid4().hex, owner_id=users[0].id)
    db.add(other)
    db.commit()
    bad = AIExecution(
        workflow_id=uuid.UUID(flow["id"]),
        workspace_id=other.id,
        input="bad",
        provider="openai-compatible",
        model="test",
        created_by=users[0].id,
        idempotency_key="mismatch",
    )
    db.add(bad)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_provider_configuration_is_private(client, tenant, monkeypatch):
    _, _, headers, _ = tenant
    monkeypatch.setattr(settings, "AI_API_KEY", SecretStr("sensitive-test-key"))
    monkeypatch.setattr(settings, "AI_BASE_URL", "https://provider.example/v1")
    result = client.get(f"{PREFIX}/operations/providers", headers=headers[0])
    assert result.json()[0]["configured"] is True
    assert (
        "sensitive-test-key" not in result.text
        and "provider.example" not in result.text
    )


@pytest.mark.parametrize(
    "mode",
    [
        "success",
        "missing_usage",
        "http_error",
        "timeout",
        "invalid",
        "negative_usage",
        "oversize",
    ],
)
def test_openai_compatible_adapter(mode, monkeypatch):
    monkeypatch.setattr(settings, "AI_API_KEY", SecretStr("test-only"))
    monkeypatch.setattr(settings, "AI_BASE_URL", "https://provider.example/v1")

    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-only"
        if mode == "http_error":
            return httpx.Response(401, text="sensitive-remote-body")
        if mode == "timeout":
            raise httpx.ReadTimeout("sensitive-remote-body")
        if mode == "invalid":
            return httpx.Response(200, json={"choices": []})
        if mode == "oversize":
            return httpx.Response(200, content=b"x" * 1000001)
        data = {"choices": [{"message": {"content": "hello"}}]}
        if mode != "missing_usage":
            data["usage"] = {
                "prompt_tokens": 2,
                "completion_tokens": 3,
                "total_tokens": -1 if mode == "negative_usage" else 5,
            }
        return httpx.Response(200, json=data)

    provider = OpenAICompatibleProvider(httpx.MockTransport(handler))
    if mode in {"success", "missing_usage"}:
        result = provider.generate(
            model="test",
            system_prompt="system",
            prompt="user",
            temperature=0.7,
            max_output_tokens=10,
        )
        assert result.output == "hello"
        assert result.total_tokens == (None if mode == "missing_usage" else 5)
    else:
        with pytest.raises(ProviderError) as error:
            provider.generate(
                model="test",
                system_prompt="system",
                prompt="user",
                temperature=0.7,
                max_output_tokens=10,
            )
        assert "sensitive-remote-body" not in str(error.value)
