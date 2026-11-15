"""Ciclo de vida del alquiler, reglas de flota, métricas y paginación."""

import pytest

from app.routers import rentals as rentals_router
from app.routers import vehicles as vehicles_router


def _status(agency, rental, status):
    return agency.post(f"/rentals/{rental['id']}/status", json={"status": status})


def test_full_lifecycle_reserved_active_returned(make_agency, today, future):
    agency = make_agency("owner@a.com")
    rental = agency.book(agency.vehicle(), agency.customer(), today, future(3)).json()
    assert rental["status"] == "reserved"

    assert _status(agency, rental, "returned").status_code == 409  # no salió: no puede volver
    assert _status(agency, rental, "active").json()["status"] == "active"
    assert _status(agency, rental, "cancelled").status_code == 409  # ya entregado

    returned = _status(agency, rental, "returned").json()
    assert returned["status"] == "returned"
    assert returned["returned_at"] is not None
    assert returned["late_fee"] == "0.00"  # devuelto antes de tiempo
    assert _status(agency, rental, "active").status_code == 409  # estado final


def test_cannot_hand_over_before_start_date(make_agency, future):
    agency = make_agency("owner@a.com")
    rental = agency.book(agency.vehicle(), agency.customer(), future(2), future(4)).json()

    response = _status(agency, rental, "active")
    assert response.status_code == 409
    assert "start_date" in response.json()["detail"]


def test_late_return_charges_late_fee(make_agency, today, future, monkeypatch):
    agency = make_agency("owner@a.com")
    car = agency.vehicle(rate="40.00")
    rental = agency.book(car, agency.customer(), today, future(2)).json()
    _status(agency, rental, "active")

    # "Viajamos" 3 días después de la fecha de devolución pactada.
    monkeypatch.setattr(rentals_router, "today", lambda: future(5))
    returned = _status(agency, rental, "returned").json()

    assert returned["late_fee"] == "180.00"  # 3 días × 40 × 1.5


def test_vehicle_with_pending_bookings_cannot_go_to_maintenance(make_agency, today, future, monkeypatch):
    agency = make_agency("owner@a.com")
    car = agency.vehicle()
    agency.book(car, agency.customer(), future(10), future(12))

    response = agency.patch(f"/vehicles/{car['id']}", json={"status": "maintenance"})
    assert response.status_code == 409
    assert "pending" in response.json()["detail"]

    # Pasada la reserva, ya no bloquea.
    monkeypatch.setattr(vehicles_router, "today", lambda: future(12))
    assert agency.patch(f"/vehicles/{car['id']}", json={"status": "maintenance"}).status_code == 200


def test_vehicle_with_history_cannot_be_deleted_only_retired(make_agency, today, future):
    agency = make_agency("owner@a.com")
    car = agency.vehicle()
    rental = agency.book(car, agency.customer(), today, future(1)).json()
    _status(agency, rental, "cancelled")

    assert agency.delete(f"/vehicles/{car['id']}").status_code == 409
    assert agency.patch(f"/vehicles/{car['id']}", json={"status": "retired"}).json()["status"] == "retired"


def test_customer_with_history_cannot_be_deleted(make_agency, future):
    agency = make_agency("owner@a.com")
    customer = agency.customer()
    agency.book(agency.vehicle(), customer, future(1), future(2))
    assert agency.delete(f"/customers/{customer['id']}").status_code == 409

    unused = agency.customer()
    assert agency.delete(f"/customers/{unused['id']}").status_code == 204


def test_patch_ignores_explicit_null_on_required_fields(make_agency):
    agency = make_agency("owner@a.com")
    car = agency.vehicle("KEEP01")
    updated = agency.patch(f"/vehicles/{car['id']}", json={"plate": None, "color": "Rojo"}).json()
    assert updated["plate"] == "KEEP01"
    assert updated["color"] == "Rojo"


def test_dashboard_summary_and_agenda(make_agency, today, future):
    agency = make_agency("owner@a.com")
    customer = agency.customer()
    out_now, upcoming, _idle = agency.vehicle("OUT001", "50.00"), agency.vehicle("UPC001"), agency.vehicle("IDL001")
    active = agency.book(out_now, customer, today, future(4)).json()
    _status(agency, active, "active")
    agency.book(upcoming, customer, future(2), future(5))

    summary = agency.get("/dashboard/summary").json()
    assert summary["vehicles_total"] == 3
    assert summary["vehicles_available_today"] == 2  # el que está fuera no cuenta
    assert summary["rentals_active"] == 1
    assert summary["rentals_reserved"] == 1
    assert summary["rentals_overdue"] == 0
    assert summary["revenue_current_month"] == "200.00"  # solo cuenta lo que ya salió (no la reserva)

    agenda = agency.get("/dashboard/agenda").json()
    assert [r["vehicle"]["plate"] for r in agenda["pickups"]] == ["UPC001"]
    assert [r["vehicle"]["plate"] for r in agenda["returns"]] == ["OUT001"]


def test_revenue_by_month_fills_empty_months(make_agency):
    agency = make_agency("owner@a.com")
    months = agency.get("/dashboard/revenue", params={"months": 3}).json()
    assert len(months) == 3
    assert all(m["revenue"] == "0.00" and m["rentals"] == 0 for m in months)


@pytest.mark.parametrize("path", ["/vehicles", "/customers", "/rentals"])
def test_list_endpoints_paginate_with_total_count_header(make_agency, future, path):
    agency = make_agency("owner@a.com")
    customer = agency.customer()
    for index in range(4):
        car = agency.vehicle(f"PAG00{index}")
        agency.book(car, customer, future(1), future(2))
        agency.customer()

    first = agency.get(path, params={"limit": 2, "offset": 0})
    rest = agency.get(path, params={"limit": 2, "offset": 2})
    total = int(first.headers["x-total-count"])
    assert total >= 4
    assert len(first.json()) == 2
    ids = {item["id"] for item in first.json()} | {item["id"] for item in rest.json()}
    assert len(ids) == 4  # sin repetidos entre páginas


def test_search(make_agency, future):
    agency = make_agency("owner@a.com")
    car = agency.vehicle("SRCH01")
    customer = agency.post("/customers", json={"document_id": "V-555", "full_name": "Ana 100% Real"}).json()
    agency.book(car, customer, future(1), future(2))

    assert [v["plate"] for v in agency.get("/vehicles", params={"q": "srch"}).json()] == ["SRCH01"]
    assert len(agency.get("/customers", params={"q": "100%"}).json()) == 1
    assert agency.get("/customers", params={"q": "%"}).json() != []  # el % literal sí aparece en el nombre
    assert agency.get("/customers", params={"q": "_"}).json() == []  # comodines neutralizados
    assert len(agency.get("/rentals", params={"q": "V-555"}).json()) == 1


def test_cors_exposes_total_count_header(client):
    response = client.options(
        "/vehicles",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    simple = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert "x-total-count" in simple.headers.get("access-control-expose-headers", "").lower()
