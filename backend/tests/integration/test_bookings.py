"""La garantía central del sistema: no puede haber dobles reservas."""

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient


def test_overlapping_booking_is_rejected_with_409(make_agency, future):
    agency = make_agency("owner@a.com")
    car, customer = agency.vehicle(), agency.customer()

    assert agency.book(car, customer, future(10), future(15)).status_code == 201
    response = agency.book(car, customer, future(12), future(20))

    assert response.status_code == 409
    assert response.json()["detail"] == "Vehicle is already booked in that period"


def test_back_to_back_bookings_are_allowed(make_agency, future):
    # Rango semiabierto: el carro vuelve el día 15 y puede salir de nuevo ese mismo día.
    agency = make_agency("owner@a.com")
    car, customer = agency.vehicle(), agency.customer()

    assert agency.book(car, customer, future(10), future(15)).status_code == 201
    assert agency.book(car, customer, future(15), future(20)).status_code == 201


def test_cancelled_booking_frees_the_vehicle(make_agency, future):
    agency = make_agency("owner@a.com")
    car, customer = agency.vehicle(), agency.customer()
    rental = agency.book(car, customer, future(10), future(15)).json()

    assert agency.post(f"/rentals/{rental['id']}/status", json={"status": "cancelled"}).status_code == 200
    assert agency.book(car, customer, future(10), future(15)).status_code == 201


def test_concurrent_requests_cannot_double_book(client, make_agency, future):
    """Carrera real: 8 peticiones SIMULTÁNEAS por el mismo carro y fechas.

    Una comprobación previa en el código ("¿está libre?") dejaría pasar varias.
    Como la garantía vive en PostgreSQL (EXCLUDE), exactamente una gana.
    """
    agency = make_agency("owner@a.com")
    car, customer = agency.vehicle(), agency.customer()
    payload = {
        "vehicle_id": car["id"],
        "customer_id": customer["id"],
        "start_date": future(5).isoformat(),
        "end_date": future(9).isoformat(),
    }

    def attempt(_):
        with TestClient(client.app) as own_client:  # un cliente por hilo
            return own_client.post("/rentals", json=payload, headers=agency.headers).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = sorted(pool.map(attempt, range(8)))

    assert codes == [201] + [409] * 7
    assert agency.get("/rentals").headers["x-total-count"] == "1"


def test_total_uses_the_rate_at_booking_time(make_agency, future):
    agency = make_agency("owner@a.com")
    car, customer = agency.vehicle(rate="40.00"), agency.customer()
    rental = agency.book(car, customer, future(1), future(6)).json()
    assert rental["total_amount"] == "200.00"

    # Subir el precio después NO cambia un alquiler ya reservado.
    agency.patch(f"/vehicles/{car['id']}", json={"daily_rate": "99.00"})
    assert agency.get(f"/rentals/{rental['id']}").json()["total_amount"] == "200.00"


def test_booking_validations(make_agency, today, future):
    agency = make_agency("owner@a.com")
    car, customer = agency.vehicle(), agency.customer()

    assert agency.book(car, customer, future(5), future(5)).status_code == 422  # rango vacío
    assert agency.book(car, customer, future(-1), future(3)).status_code == 422  # empieza en el pasado
    assert agency.book(car, customer, today, future(1)).status_code == 201  # hoy sí se puede


def test_vehicle_in_maintenance_cannot_be_booked(make_agency, future):
    agency = make_agency("owner@a.com")
    car, customer = agency.vehicle(), agency.customer()
    agency.patch(f"/vehicles/{car['id']}", json={"status": "maintenance"})

    response = agency.book(car, customer, future(1), future(3))
    assert response.status_code == 409


def test_availability_search(make_agency, future):
    agency = make_agency("owner@a.com")
    booked, _free, in_shop = agency.vehicle("AAA111"), agency.vehicle("BBB222"), agency.vehicle("CCC333")
    customer = agency.customer()
    agency.book(booked, customer, future(10), future(15))
    agency.patch(f"/vehicles/{in_shop['id']}", json={"status": "maintenance"})

    def available(start, end):
        response = agency.get(
            "/vehicles/available", params={"start_date": future(start).isoformat(), "end_date": future(end).isoformat()}
        )
        assert response.status_code == 200
        return [v["plate"] for v in response.json()]

    assert available(12, 13) == ["BBB222"]
    assert available(15, 18) == ["AAA111", "BBB222"]  # el día de devolución ya está libre
    assert available(5, 10) == ["AAA111", "BBB222"]


def test_vehicle_with_overdue_return_is_not_available(make_agency, today, future, monkeypatch):
    """Un carro que el cliente no ha devuelto sigue fuera aunque su rango pactado haya terminado."""
    from app.routers import dashboard, rentals, vehicles

    agency = make_agency("owner@a.com")
    car, customer = agency.vehicle("LATE01"), agency.customer()
    rental = agency.book(car, customer, today, future(2)).json()
    agency.post(f"/rentals/{rental['id']}/status", json={"status": "active"})

    # Pasan 5 días: la devolución pactada (hoy + 2) venció y el carro no ha vuelto.
    for module in (dashboard, rentals, vehicles):
        monkeypatch.setattr(module, "today", lambda: future(5))

    available = agency.get(
        "/vehicles/available", params={"start_date": future(5).isoformat(), "end_date": future(7).isoformat()}
    ).json()
    assert available == []
    assert agency.get("/dashboard/summary").json()["vehicles_available_today"] == 0
    assert agency.get("/dashboard/summary").json()["rentals_overdue"] == 1

    response = agency.book(car, customer, future(5), future(7))
    assert response.status_code == 409
    assert "overdue" in response.json()["detail"]

    # Al registrar la devolución, vuelve a estar disponible.
    agency.post(f"/rentals/{rental['id']}/status", json={"status": "returned"})
    assert agency.book(car, customer, future(5), future(7)).status_code == 201
