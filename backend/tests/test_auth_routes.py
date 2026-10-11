import uuid

from fastapi.testclient import TestClient

from app.auth import router as auth_module
from app.auth.dependencies import Principal, get_current_principal
from app.auth.models import StaffInvitation
from app.core.db import get_db
from app.main import create_app
from app.users.models import ROLE_NAMES, Role, User


class FakeQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def delete(self, **_kwargs):
        return 0


class FakeSession:
    def __init__(self) -> None:
        self.user = User(id=uuid.uuid4(), email="staff@example.com", status="ACTIVE")
        self.role = Role(id=uuid.uuid4(), name="PARTICIPANT")

    def scalar(self, statement):
        selected = statement.column_descriptions[0].get("expr")
        if selected is User:
            return self.user
        if selected is Role:
            return self.role
        return None

    def scalars(self, _statement):
        class Results:
            @staticmethod
            def all():
                return []

        return Results()

    def execute(self, _statement):
        return None

    def add(self, value):
        if isinstance(value, StaffInvitation) and value.id is None:
            value.id = uuid.uuid4()

    def flush(self):
        return None

    def commit(self):
        return None

    def query(self, _model):
        return FakeQuery()


def _authorized_client(role: str) -> TestClient:
    app = create_app()
    principal = Principal(
        user=User(id=uuid.uuid4(), email="staff@example.com", status="ACTIVE"),
        roles=frozenset({role}),
    )
    session = FakeSession()

    def override_db():
        yield session

    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_db] = override_db
    return TestClient(app, raise_server_exceptions=False)


def test_only_secure_participant_otp_routes_are_mounted() -> None:
    app = create_app()
    routes = [route for route in app.routes if hasattr(route, "methods")]
    paths = {route.path for route in routes}

    assert "/api/v1/auth/otp/request" in paths
    assert "/api/v1/auth/otp/verify" in paths
    assert "/api/v1/admin/users/{user_id}/roles" in paths
    assert "/api/v1/auth/register" not in paths
    assert "/api/v1/auth/verify-otp" not in paths
    assert len(
        [route for route in routes if route.path == "/api/v1/auth/login" and "POST" in route.methods]
    ) == 1


def test_staff_invitation_and_role_assignment_follow_super_admin_matrix(monkeypatch) -> None:
    monkeypatch.setattr(auth_module, "_rate_limit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth_module, "write_audit", lambda *_args, **_kwargs: None)
    role_path = f"/api/v1/admin/users/{uuid.uuid4()}/roles"

    for role in ROLE_NAMES:
        client = _authorized_client(role)
        invite = client.post("/api/v1/auth/staff/invitations", json={"email": "new@example.com"})
        assignment = client.put(role_path, json={"roles": ["PARTICIPANT"]})
        if role == "SUPER_ADMIN":
            assert invite.status_code == 201
            assert assignment.status_code == 200
        else:
            assert invite.status_code == 403, role
            assert assignment.status_code == 403, role


def test_draw_list_is_read_only_and_limited_to_admin_auditor_roles() -> None:
    for role, expected_status in (
        ("ADMIN", 200),
        ("SUPER_ADMIN", 200),
        ("AUDITOR", 200),
        ("CAMPAIGN_MANAGER", 403),
        ("PARTICIPANT", 403),
    ):
        client = _authorized_client(role)
        response = client.get("/api/v1/admin/draws")
        assert response.status_code == expected_status, role
        if expected_status == 200:
            assert response.json() == []


def test_campaign_scheduling_permission_matches_campaign_manager_matrix() -> None:
    campaign_id = uuid.uuid4()
    manager_response = _authorized_client("CAMPAIGN_MANAGER").post(
        f"/api/v1/admin/campaigns/{campaign_id}/schedule"
    )
    admin_response = _authorized_client("ADMIN").post(
        f"/api/v1/admin/campaigns/{campaign_id}/schedule"
    )

    assert manager_response.status_code == 404
    assert admin_response.status_code == 403
