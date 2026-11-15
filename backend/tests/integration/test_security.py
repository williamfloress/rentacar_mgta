"""Aislamiento entre agencias, roles y autenticación."""

from sqlalchemy import create_engine, text

from app import ratelimit
from tests.conftest import APP_TEST_URL


def test_agency_cannot_see_or_touch_another_agencys_data(make_agency, future):
    a, b = make_agency("owner@a.com"), make_agency("owner@b.com")
    car, customer = a.vehicle(), a.customer()
    rental = a.book(car, customer, future(1), future(3)).json()

    # 404 (no 403): ni siquiera se revela que el recurso existe.
    assert b.get(f"/vehicles/{car['id']}").status_code == 404
    assert b.get(f"/customers/{customer['id']}").status_code == 404
    assert b.get(f"/rentals/{rental['id']}").status_code == 404
    assert b.patch(f"/vehicles/{car['id']}", json={"daily_rate": "1.00"}).status_code == 404
    assert b.post(f"/rentals/{rental['id']}/status", json={"status": "cancelled"}).status_code == 404

    assert b.get("/vehicles").json() == []
    assert b.get("/rentals").json() == []
    assert b.get("/dashboard/summary").json()["vehicles_total"] == 0

    # Tampoco puede reservar el carro de A con su propio cliente.
    assert b.book(car, b.customer(), future(5), future(6)).status_code == 404


def test_same_plate_and_document_are_allowed_in_different_agencies(make_agency):
    a, b = make_agency("owner@a.com"), make_agency("owner@b.com")
    a.vehicle("XYZ999")
    a.customer("V-1")
    b.vehicle("XYZ999")
    b.customer("V-1")
    assert (
        a.post(
            "/vehicles",
            json={
                "plate": "xyz999",
                "brand": "Kia",
                "model": "Rio",
                "year": 2020,
                "daily_rate": "30.00",
            },
        ).status_code
        == 409
    )  # dentro de la misma agencia la placa es única (y se normaliza)


def test_row_level_security_is_the_second_lock(make_agency):
    """Aunque la aplicación olvidara filtrar por agencia, PostgreSQL no entrega filas ajenas."""
    a = make_agency("owner@a.com")
    a.vehicle()

    engine = create_engine(APP_TEST_URL)  # el mismo rol restringido que usa la API
    with engine.connect() as conn:
        # Sin contexto de agencia: cero filas, aunque la tabla tiene datos.
        assert conn.scalar(text("SELECT count(*) FROM vehicles")) == 0
        conn.execute(text("SELECT set_config('app.tenant_id', gen_random_uuid()::text, true)"))
        assert conn.scalar(text("SELECT count(*) FROM vehicles")) == 0
    engine.dispose()


def test_agents_cannot_delete_or_manage_staff(make_agency):
    owner = make_agency("owner@a.com")
    agent = owner.add_agent("agent@a.com")
    car = owner.vehicle()

    assert owner.client.delete(f"/vehicles/{car['id']}", headers=agent["headers"]).status_code == 403
    assert owner.client.get("/users", headers=agent["headers"]).status_code == 403
    assert (
        owner.client.post(
            "/vehicles",
            headers=agent["headers"],
            json={
                "plate": "AGT001",
                "brand": "Kia",
                "model": "Rio",
                "year": 2020,
                "daily_rate": "30.00",
            },
        ).status_code
        == 201
    )  # pero sí opera el día a día

    assert owner.delete(f"/vehicles/{car['id']}").status_code == 204


def test_deactivated_user_token_stops_working_immediately(make_agency):
    owner = make_agency("owner@a.com")
    agent = owner.add_agent("agent@a.com")
    assert owner.client.get("/auth/me", headers=agent["headers"]).status_code == 200

    assert owner.post(f"/users/{agent['id']}/deactivate").status_code == 200

    assert owner.client.get("/auth/me", headers=agent["headers"]).status_code == 401
    login = owner.client.post("/auth/login", data={"username": "agent@a.com", "password": "password-1234"})
    assert login.status_code == 401


def test_owner_cannot_deactivate_themselves(make_agency):
    owner = make_agency("owner@a.com")
    me = owner.get("/auth/me").json()
    assert owner.post(f"/users/{me['id']}/deactivate").status_code == 409


def test_login(client, make_agency):
    make_agency("Owner@A.com".lower())
    ok = client.post("/auth/login", data={"username": "OWNER@a.com", "password": "password-1234"})
    assert ok.status_code == 200  # el email no distingue mayúsculas

    wrong_password = client.post("/auth/login", data={"username": "owner@a.com", "password": "nope-nope-nope"})
    unknown_email = client.post("/auth/login", data={"username": "ghost@a.com", "password": "password-1234"})
    # Misma respuesta en ambos casos: no se revela qué emails existen.
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_email_is_unique_across_agencies(client, make_agency):
    make_agency("owner@a.com")
    response = client.post(
        "/auth/register",
        json={
            "agency_name": "Otra",
            "full_name": "Otro",
            "email": "owner@a.com",
            "password": "password-1234",
        },
    )
    assert response.status_code == 409


def test_invalid_tokens_are_rejected(client):
    for token in ["garbage", "eyJhbGciOiJub25lIn0.eyJzdWIiOiJ4In0."]:  # basura y "alg=none"
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.get("/vehicles").status_code == 401


def test_login_is_rate_limited(client, make_agency, monkeypatch):
    make_agency("owner@a.com")
    monkeypatch.setattr(ratelimit._settings, "auth_rate_limit_attempts", 3)
    monkeypatch.setattr(ratelimit.auth_limiter, "max_attempts", 3)
    ratelimit.auth_limiter.reset()

    codes = [
        client.post("/auth/login", data={"username": "owner@a.com", "password": "wrong-password"}).status_code
        for _ in range(4)
    ]
    assert codes == [401, 401, 401, 429]
    ratelimit.auth_limiter.reset()


def test_security_headers_present(client):
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_me_includes_agency_profile(make_agency):
    agency = make_agency("owner@a.com")
    me = agency.get("/auth/me").json()
    assert me["agency_name"] == "Agencia owner@a.com"
    assert me["currency"] == "USD"
    assert me["role"] == "owner"
    assert "password_hash" not in me
