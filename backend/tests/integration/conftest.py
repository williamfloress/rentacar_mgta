"""Fixtures de integración: base de datos temporal, cliente HTTP y ayudantes."""

import os
import uuid
from collections.abc import Callable
from datetime import date, timedelta

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from tests.conftest import ADMIN_URL, APP_ROLE, APP_ROLE_PASSWORD, OWNER_TEST_URL, TEST_DB

pytestmark = pytest.mark.integration
BACKEND_DIR = __import__("pathlib").Path(__file__).resolve().parents[2]


def pytest_collection_modifyitems(items):
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def database():
    """Crea la base temporal, aplica las migraciones REALES (Alembic) y crea el rol restringido."""
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
            conn.execute(text(f"DROP ROLE IF EXISTS {APP_ROLE}"))
            conn.execute(text(f"CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{APP_ROLE_PASSWORD}' NOSUPERUSER NOBYPASSRLS"))
            conn.execute(text(f"CREATE DATABASE {TEST_DB}"))
    except OperationalError as exc:
        message = f"PostgreSQL no disponible para pruebas de integración: {exc.orig}"
        # En CI (REQUIRE_DB=1) es un fallo: un "verde" sin haber probado nada sería engañoso.
        if os.environ.get("REQUIRE_DB") == "1":
            pytest.fail(message)
        pytest.skip(message)

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(config, "head")

    owner = create_engine(OWNER_TEST_URL, isolation_level="AUTOCOMMIT")
    with owner.connect() as conn:
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}"))
        conn.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE}"))

    yield owner

    from app.database import engine as app_engine

    app_engine.dispose()
    owner.dispose()
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
        conn.execute(text(f"DROP ROLE IF EXISTS {APP_ROLE}"))
    admin.dispose()


@pytest.fixture(autouse=True)
def clean_database(database):
    """Cada prueba empieza con la base vacía. TRUNCATE ... CASCADE vacía todo lo que cuelga de tenants."""
    yield
    with database.connect() as conn:
        conn.execute(text("TRUNCATE tenants CASCADE"))


@pytest.fixture
def client(database) -> TestClient:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def today() -> date:
    from app.clock import today as agency_today

    return agency_today()


# ------------------------------------------------------------------ ayudantes
class Agency:
    """Una agencia registrada en la API, con atajos para crear datos."""

    def __init__(self, client: TestClient, email: str) -> None:
        self.client = client
        self.email = email
        response = client.post(
            "/auth/register",
            json={"agency_name": f"Agencia {email}", "full_name": "Dueño", "email": email, "password": "password-1234"},
        )
        assert response.status_code == 201, response.text
        self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    def get(self, url: str, **kwargs):
        return self.client.get(url, headers=self.headers, **kwargs)

    def post(self, url: str, **kwargs):
        return self.client.post(url, headers=self.headers, **kwargs)

    def patch(self, url: str, **kwargs):
        return self.client.patch(url, headers=self.headers, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.client.delete(url, headers=self.headers, **kwargs)

    def vehicle(self, plate: str | None = None, rate: str = "40.00") -> dict:
        response = self.post(
            "/vehicles",
            json={
                "plate": plate or f"T{uuid.uuid4().hex[:6]}",
                "brand": "Toyota",
                "model": "Corolla",
                "year": 2022,
                "daily_rate": rate,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    def customer(self, document_id: str | None = None) -> dict:
        response = self.post(
            "/customers",
            json={"document_id": document_id or f"V-{uuid.uuid4().hex[:8]}", "full_name": "Cliente Prueba"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    def book(self, vehicle: dict, customer: dict, start: date, end: date):
        return self.post(
            "/rentals",
            json={
                "vehicle_id": vehicle["id"],
                "customer_id": customer["id"],
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
        )

    def add_agent(self, email: str) -> dict:
        response = self.post("/users", json={"email": email, "full_name": "Agente", "password": "password-1234"})
        assert response.status_code == 201, response.text
        token = self.client.post("/auth/login", data={"username": email, "password": "password-1234"})
        assert token.status_code == 200, token.text
        return {"id": response.json()["id"], "headers": {"Authorization": f"Bearer {token.json()['access_token']}"}}


@pytest.fixture
def make_agency(client) -> Callable[[str], Agency]:
    return lambda email: Agency(client, email)


@pytest.fixture
def future(today) -> Callable[[int], date]:
    """future(n) = hoy + n días (las reservas nuevas no pueden empezar en el pasado)."""
    return lambda days: today + timedelta(days=days)
