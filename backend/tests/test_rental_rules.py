from datetime import date

import pytest

from app.domain.rental_rules import (
    ALLOWED_TRANSITIONS,
    BLOCKING_STATUSES,
    InvalidTransition,
    RentalStatus,
    ensure_can_start,
    ensure_transition,
    validate_new_rental_dates,
)

S = RentalStatus


@pytest.mark.parametrize(
    "current,target",
    [(S.RESERVED, S.ACTIVE), (S.RESERVED, S.CANCELLED), (S.ACTIVE, S.RETURNED)],
)
def test_valid_transitions(current, target):
    ensure_transition(current, target)  # no debe lanzar


@pytest.mark.parametrize(
    "current,target",
    [
        (S.RESERVED, S.RETURNED),  # no se puede devolver algo que no salió
        (S.ACTIVE, S.CANCELLED),  # una vez entregado ya no se cancela
        (S.ACTIVE, S.RESERVED),
        (S.RETURNED, S.ACTIVE),  # estados finales: no hay vuelta atrás
        (S.CANCELLED, S.ACTIVE),
        (S.RETURNED, S.RETURNED),
    ],
)
def test_invalid_transitions(current, target):
    with pytest.raises(InvalidTransition):
        ensure_transition(current, target)


def test_final_states_have_no_exits():
    assert ALLOWED_TRANSITIONS[S.RETURNED] == frozenset()
    assert ALLOWED_TRANSITIONS[S.CANCELLED] == frozenset()


def test_blocking_statuses_match_database_constraint():
    # Debe coincidir con: WHERE (status IN ('reserved', 'active')) del esquema SQL.
    assert {s.value for s in BLOCKING_STATUSES} == {"reserved", "active"}


def test_every_status_is_covered_by_the_state_machine():
    assert set(ALLOWED_TRANSITIONS) == set(RentalStatus)


def test_new_rental_dates_ok_today_and_future():
    today = date(2030, 1, 10)
    validate_new_rental_dates(date(2030, 1, 10), date(2030, 1, 12), today)
    validate_new_rental_dates(date(2030, 2, 1), date(2030, 2, 3), today)


def test_new_rental_dates_reject_past_start():
    with pytest.raises(ValueError, match="past"):
        validate_new_rental_dates(date(2030, 1, 9), date(2030, 1, 12), date(2030, 1, 10))


def test_new_rental_dates_reject_end_not_after_start():
    with pytest.raises(ValueError, match="after"):
        validate_new_rental_dates(date(2030, 1, 10), date(2030, 1, 10), date(2030, 1, 1))


def test_rental_can_start_on_or_after_its_start_date():
    ensure_can_start(date(2030, 1, 10), today=date(2030, 1, 10))
    ensure_can_start(date(2030, 1, 10), today=date(2030, 1, 12))  # el cliente llegó tarde


def test_rental_cannot_start_before_its_start_date():
    # entregar antes ocuparía días fuera del rango protegido por la base de datos
    with pytest.raises(InvalidTransition):
        ensure_can_start(date(2030, 1, 10), today=date(2030, 1, 9))
