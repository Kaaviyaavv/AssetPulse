"""Depreciation unit tests. Proposal 5.4 guardrail:
accumulated_depr + net_book_value must always equal purchase_price.
"""
from datetime import date
from app.services import depreciation as d


def test_straight_line_half_life():
    acc, nbv = d.straight_line(100000, 5, 2.5)
    assert acc == 50000.00
    assert nbv == 50000.00


def test_straight_line_never_exceeds_price():
    acc, nbv = d.straight_line(100000, 5, 10)  # way past useful life
    assert acc == 100000.00
    assert nbv == 0.00


def test_diminishing_balance_first_year():
    acc, nbv = d.diminishing_balance(100000, 5, 1)  # rate = 0.4
    assert nbv == 60000.00
    assert acc == 40000.00


def test_guardrail_sum_equals_price_straight():
    price = 87000
    acc, nbv = d.straight_line(price, 4, 1.7)
    assert round(acc + nbv, 2) == price


def test_guardrail_sum_equals_price_diminishing():
    price = 250000
    acc, nbv = d.diminishing_balance(price, 5, 3.2)
    assert round(acc + nbv, 2) == price


def test_compute_dispatch():
    acc, nbv = d.compute(50000, 5, "diminishing_balance",
                         date(2023, 1, 1), date(2024, 1, 1))
    assert acc + nbv == 50000
