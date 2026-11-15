from datetime import date
from decimal import Decimal

import pytest

from app.domain.pricing import calculate_late_fee, calculate_total, money, rental_days


def test_rental_days_is_half_open_range():
    # del 10 al 15 son 5 días: el día de devolución no se cobra
    assert rental_days(date(2030, 1, 10), date(2030, 1, 15)) == 5


@pytest.mark.parametrize("end", [date(2030, 1, 10), date(2030, 1, 9)])
def test_rental_days_rejects_empty_or_inverted_range(end):
    with pytest.raises(ValueError):
        rental_days(date(2030, 1, 10), end)


def test_total_is_rate_times_days():
    assert calculate_total(Decimal("40.00"), date(2030, 1, 10), date(2030, 1, 15)) == Decimal("200.00")


def test_total_rounds_half_up_to_cents():
    # 33.335 × 1 día → 33.34 (mitad hacia arriba), no 33.33 como haría float/banker's
    assert calculate_total(Decimal("33.335"), date(2030, 1, 1), date(2030, 1, 2)) == Decimal("33.34")


def test_money_never_uses_float_artifacts():
    assert money(Decimal("0.1") + Decimal("0.2")) == Decimal("0.30")


def test_no_late_fee_when_returned_on_time_or_early():
    end = date(2030, 1, 15)
    assert calculate_late_fee(Decimal("40"), end, date(2030, 1, 15), Decimal("1.5")) == Decimal("0.00")
    assert calculate_late_fee(Decimal("40"), end, date(2030, 1, 12), Decimal("1.5")) == Decimal("0.00")


def test_late_fee_charges_multiplier_per_late_day():
    # 2 días tarde × 40 × 1.5 = 120.00
    assert calculate_late_fee(Decimal("40"), date(2030, 1, 15), date(2030, 1, 17), Decimal("1.5")) == Decimal("120.00")
