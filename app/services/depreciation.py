"""Depreciation math. Pure functions so they are trivial to unit-test.

Guardrail (from proposal 5.4): accumulated_depr + net_book_value must always
equal purchase_price at any point in time.
"""
from datetime import date


def straight_line(purchase_price: float, useful_life_yrs: int, years_elapsed: float):
    """Equal reduction each year over useful life."""
    annual = purchase_price / useful_life_yrs
    accumulated = min(annual * years_elapsed, purchase_price)
    nbv = purchase_price - accumulated
    return round(accumulated, 2), round(nbv, 2)


def diminishing_balance(purchase_price: float, useful_life_yrs: int, years_elapsed: float):
    """Fixed percentage of remaining book value each year (double-declining)."""
    rate = 2.0 / useful_life_yrs
    nbv = purchase_price
    full_years = int(years_elapsed)
    for _ in range(full_years):
        nbv -= nbv * rate
    # partial year
    frac = years_elapsed - full_years
    nbv -= nbv * rate * frac
    nbv = max(nbv, 0.0)
    accumulated = purchase_price - nbv
    return round(accumulated, 2), round(nbv, 2)


def years_between(purchase_date: date, as_of: date) -> float:
    return (as_of - purchase_date).days / 365.25


def compute(purchase_price, useful_life_yrs, method, purchase_date, as_of):
    yrs = years_between(purchase_date, as_of)
    if method == "diminishing_balance":
        return diminishing_balance(purchase_price, useful_life_yrs, yrs)
    return straight_line(purchase_price, useful_life_yrs, yrs)
