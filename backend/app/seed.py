"""Datos de demostración: una agencia con flota, clientes y 6 meses de historial.

Uso:
    python -m app.seed            # (re)crea la agencia demo
Con Docker se ejecuta solo al arrancar si SEED_DEMO=true.

Es IDEMPOTENTE y solo afecta a la agencia demo: si ya existe, la borra (en
cascada) y la vuelve a crear. Así la demo pública se "resetea" en cada
reinicio y nadie puede dejarla rota para el siguiente visitante.

Las fechas se calculan relativas a HOY, de modo que siempre hay alquileres
pasados, en curso, atrasados y futuros. La semilla del generador aleatorio es
fija: los datos son los mismos en cada ejecución del mismo día.
"""

import random
import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, delete, select

from app.clock import today
from app.config import get_settings
from app.database import SessionLocal
from app.domain.pricing import calculate_late_fee, calculate_total
from app.models import AuditLog, Customer, Rental, Tenant, User, Vehicle
from app.security import hash_password

DEMO_OWNER_EMAIL = "demo@rentacar.dev"
DEMO_AGENT_EMAIL = "agente@rentacar.dev"
DEMO_PASSWORD = "demo-rentacar"  # pública a propósito: se muestra en la pantalla de login

VEHICLES = [
    # placa, marca, modelo, color, año, tarifa diaria
    ("AB123CD", "Toyota", "Corolla", "Blanco", 2022, "45.00"),
    ("AC456EF", "Toyota", "Hilux", "Gris", 2021, "75.00"),
    ("AD789GH", "Chevrolet", "Aveo", "Rojo", 2019, "30.00"),
    ("AE012IJ", "Ford", "Fiesta", "Azul", 2020, "32.00"),
    ("AF345KL", "Kia", "Rio", "Plata", 2023, "38.00"),
    ("AG678MN", "Hyundai", "Tucson", "Negro", 2022, "65.00"),
    ("AH901OP", "Toyota", "Fortuner", "Blanco", 2023, "90.00"),
    ("AI234QR", "Chery", "Tiggo 4", "Gris", 2024, "48.00"),
    ("AJ567ST", "Renault", "Logan", "Beige", 2018, "28.00"),
    ("AK890UV", "Mitsubishi", "Lancer", "Negro", 2017, "35.00"),
    ("AL135WX", "Jeep", "Grand Cherokee", "Vinotinto", 2020, "110.00"),
    ("AM246YZ", "Nissan", "Sentra", "Plata", 2021, "42.00"),
]
MAINTENANCE_PLATE = "AK890UV"

CUSTOMERS = [
    ("V-12.345.678", "María Fernanda González", "+58 412-555-0101", "maria.gonzalez@example.com", "Chacao, Caracas"),
    ("V-14.567.890", "José Rafael Pérez", "+58 414-555-0102", "jose.perez@example.com", "Los Palos Grandes, Caracas"),
    ("V-18.234.567", "Andreína Rodríguez", "+58 424-555-0103", None, "El Cafetal, Caracas"),
    ("V-20.111.222", "Luis Alberto Hernández", "+58 416-555-0104", "luis.hernandez@example.com", "Valencia, Carabobo"),
    ("V-9.876.543", "Carmen Elena Díaz", "+58 412-555-0105", "carmen.diaz@example.com", "Maracay, Aragua"),
    ("V-22.333.444", "Gabriel Martínez", "+58 414-555-0106", None, None),
    ("E-84.123.456", "Sofía Rossi", "+58 424-555-0107", "sofia.rossi@example.com", "Altamira, Caracas"),
    ("V-16.789.012", "Pedro José Ramírez", "+58 412-555-0108", "pedro.ramirez@example.com", "Barquisimeto, Lara"),
    ("V-25.678.901", "Valentina Torres", "+58 416-555-0109", "valentina.torres@example.com", "Mérida, Mérida"),
    ("V-11.222.333", "Ricardo Morales", "+58 414-555-0110", None, "Puerto La Cruz, Anzoátegui"),
    ("V-19.444.555", "Daniela Castillo", "+58 424-555-0111", "daniela.castillo@example.com", "Las Mercedes, Caracas"),
    ("P-AB123456", "Thomas Müller", "+49 151-555-0112", "thomas.muller@example.com", "Berlín, Alemania"),
    ("V-21.987.654", "Alejandro Rivas", "+58 412-555-0113", "alejandro.rivas@example.com", "La Trinidad, Caracas"),
    ("V-15.000.111", "Isabel Medina", "+58 416-555-0114", None, "San Antonio de los Altos, Miranda"),
]


def _owner_session():
    """Sesión con el rol DUEÑO (el de las migraciones): esta es una tarea administrativa.

    Ese rol sigue sujeto a RLS (FORCE ROW LEVEL SECURITY), así que igualmente
    hay que declarar el contexto de agencia en session.info.
    """
    settings = get_settings()
    url = settings.migrations_database_url or settings.database_url
    engine = create_engine(url, connect_args={"prepare_threshold": None})
    return SessionLocal(bind=engine), engine


def _remove_existing_demo(db) -> None:
    db.info["login_email"] = DEMO_OWNER_EMAIL
    owner = db.scalar(select(User).where(User.email == DEMO_OWNER_EMAIL))
    db.commit()
    if owner is None:
        return
    db.info["tenant_id"] = str(owner.tenant_id)
    # ON DELETE CASCADE elimina usuarios, flota, clientes, alquileres y auditoría.
    db.execute(delete(Tenant).where(Tenant.id == owner.tenant_id))
    db.commit()


def _generate_rentals(rng: random.Random, tenant_id, vehicles, customers, owner_id, now: date):
    """Historial por vehículo, sin solapamientos: cada alquiler empieza cuando acaba el anterior (o después)."""
    multiplier = get_settings().late_fee_multiplier
    rentals: list[Rental] = []
    overdue_done = False

    for vehicle in vehicles:
        cursor = now - timedelta(days=185) + timedelta(days=rng.randint(0, 10))
        only_past = vehicle.plate == MAINTENANCE_PLATE  # en taller: sin reservas futuras
        while True:
            start = cursor + timedelta(days=rng.randint(0, 10))
            end = start + timedelta(days=rng.randint(2, 8))
            if start > now + timedelta(days=30) or (only_past and end >= now):
                break
            rate = vehicle.daily_rate
            rental = Rental(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                vehicle_id=vehicle.id,
                customer_id=rng.choice(customers).id,
                start_date=start,
                end_date=end,
                daily_rate_snapshot=rate,
                total_amount=calculate_total(rate, start, end),
                created_by=owner_id,
                created_at=datetime.combine(start - timedelta(days=rng.randint(1, 15)), time(10), UTC),
            )
            cursor = end

            if end <= now:
                if not overdue_done and not only_past and now - timedelta(days=4) < end < now:
                    # Un caso atrasado para que la agenda muestre una alerta.
                    rental.status = "active"
                    overdue_done = True
                    rentals.append(rental)
                    break  # el carro no ha vuelto: no hay más alquileres para él
                if rng.random() < 0.06:
                    rental.status = "cancelled"
                else:
                    late_days = rng.choice([0] * 9 + [1, 2])
                    returned_on = end + timedelta(days=late_days)
                    rental.status = "returned"
                    rental.returned_at = datetime.combine(returned_on, time(17), UTC)
                    rental.late_fee = calculate_late_fee(rate, end, returned_on, multiplier)
            elif start <= now:
                rental.status = "active"
            else:
                rental.status = "cancelled" if rng.random() < 0.05 else "reserved"
            rentals.append(rental)
    return rentals


def seed() -> None:
    now = today()
    rng = random.Random(42)
    db, engine = _owner_session()
    try:
        _remove_existing_demo(db)

        tenant_id = uuid.uuid4()
        db.info["tenant_id"] = str(tenant_id)
        db.info.pop("login_email", None)

        db.add(Tenant(id=tenant_id, name="Autos del Ávila"))
        db.flush()
        password_hash = hash_password(DEMO_PASSWORD)
        owner = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=DEMO_OWNER_EMAIL,
            password_hash=password_hash,
            full_name="Juan Pérez",
            role="owner",
        )
        agent = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=DEMO_AGENT_EMAIL,
            password_hash=password_hash,
            full_name="Carlos Mendoza",
            role="agent",
        )
        db.add_all([owner, agent])

        vehicles = [
            Vehicle(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                plate=plate,
                brand=brand,
                model=model,
                color=color,
                year=year,
                daily_rate=Decimal(rate),
            )
            for plate, brand, model, color, year, rate in VEHICLES
        ]
        customers = [
            Customer(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                document_id=doc,
                full_name=name,
                phone=phone,
                email=email,
                address=address,
            )
            for doc, name, phone, email, address in CUSTOMERS
        ]
        db.add_all(vehicles + customers)
        db.flush()

        rentals = _generate_rentals(rng, tenant_id, vehicles, customers, owner.id, now)
        db.add_all(rentals)
        for vehicle in vehicles:
            if vehicle.plate == MAINTENANCE_PLATE:
                vehicle.status = "maintenance"
        db.add(
            AuditLog(
                tenant_id=tenant_id, user_id=owner.id, action="tenant.seeded", entity="tenant", entity_id=tenant_id
            )
        )
        db.commit()
        print(f"Demo seeded: {len(vehicles)} vehicles, {len(customers)} customers, {len(rentals)} rentals")
        print(f"  owner: {DEMO_OWNER_EMAIL} / {DEMO_PASSWORD}")
        print(f"  agent: {DEMO_AGENT_EMAIL} / {DEMO_PASSWORD}")
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    seed()
