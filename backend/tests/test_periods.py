from datetime import date

from app.domain.periods import add_months, last_month_starts, month_start


def test_month_start():
    assert month_start(date(2026, 11, 14)) == date(2026, 11, 1)


def test_add_months_crosses_year_boundaries():
    assert add_months(date(2026, 11, 1), 2) == date(2027, 1, 1)
    assert add_months(date(2026, 1, 1), -1) == date(2025, 12, 1)
    assert add_months(date(2026, 3, 1), -14) == date(2025, 1, 1)


def test_last_month_starts_are_oldest_first_and_include_current():
    assert last_month_starts(date(2026, 2, 20), 3) == [
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    ]
