"""Number formatting helpers (Indian digit grouping: 12,34,567)."""
from __future__ import annotations

import math

import config as cfg


def _is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def indian_grouping(value, decimals: int = 0) -> str:
    """1234567.8 -> '12,34,568' (decimals=0) ; missing -> 'N/A'."""
    if _is_missing(value):
        return "N/A"
    rounded = round(float(value), decimals)
    negative = rounded < 0
    whole, _, frac = f"{abs(rounded):.{decimals}f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    text = whole + (f".{frac}" if decimals else "")
    return f"-{text}" if negative else text


def number(value, decimals: int = 0) -> str:
    return indian_grouping(value, decimals)


def currency(value, decimals: int = 0) -> str:
    """Full precision with symbol, e.g. ₹12,34,567."""
    if _is_missing(value):
        return "N/A"
    text = indian_grouping(abs(float(value)), decimals)
    sign = "-" if round(float(value), decimals) < 0 else ""
    return f"{sign}{cfg.CURRENCY_SYMBOL}{text}"


def currency_compact(value) -> str:
    """Short form for KPI cards: ₹4.56 Cr, ₹7.80 L, ₹45,000."""
    if _is_missing(value):
        return "N/A"
    v = float(value)
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a >= 1e7:
        return f"{sign}{cfg.CURRENCY_SYMBOL}{a / 1e7:.2f} Cr"
    if a >= 1e5:
        return f"{sign}{cfg.CURRENCY_SYMBOL}{a / 1e5:.2f} L"
    return currency(v)


def percent(value, decimals: int = 1) -> str:
    return "N/A" if _is_missing(value) else f"{float(value):.{decimals}f}%"
