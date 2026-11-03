"""Unit normalisation (P2.2). pint-based canonicalisation that FAILS CLOSED.

A physical quantity in a plan may arrive as a bare number (assumed already in the
canonical unit), a string like "350 degC", or a mapping {"value": 350, "unit":
"degC"}. ``to_canonical`` converts it to a float in the dimension's canonical unit.
Anything unparseable, dimensionless-where-a-dimension-is-required, or
dimensionally wrong (e.g. a volume supplied where a temperature is expected) raises
``UnitError`` so the boundary can reject the plan. Nothing is silently coerced.

Canonical units (benign OER parameter world):
  temperature -> degree_Celsius, time -> minute, volume -> milliliter,
  length -> nanometer, frequency -> hertz.
"""

from __future__ import annotations

from typing import Union

import pint

_UREG = pint.UnitRegistry()
Number = Union[int, float]

# dimension name -> canonical unit string
CANONICAL = {
    "temperature": "degree_Celsius",
    "time": "minute",
    "volume": "milliliter",
    "length": "nanometer",
    "frequency": "hertz",
}


class UnitError(ValueError):
    """Raised when a quantity cannot be parsed or is dimensionally wrong."""


def _as_quantity(value) -> pint.Quantity:
    """Build a pint Quantity from number | str | {'value','unit'}; else UnitError."""
    try:
        if isinstance(value, bool):
            raise UnitError(f"boolean is not a quantity: {value!r}")
        if isinstance(value, (int, float)):
            return _UREG.Quantity(value)  # dimensionless; caller supplies dimension
        if isinstance(value, str):
            q = _UREG.Quantity(value)
            if isinstance(q, (int, float)):
                return _UREG.Quantity(q)
            return q
        if isinstance(value, dict):
            if "value" not in value or "unit" not in value:
                raise UnitError(f"quantity mapping needs 'value' and 'unit': {value!r}")
            return _UREG.Quantity(value["value"], value["unit"])
    except UnitError:
        raise
    except Exception as exc:  # pint parse errors, undefined units, etc.
        raise UnitError(f"unparseable quantity {value!r}: {exc}") from None
    raise UnitError(f"unsupported quantity type {type(value).__name__}: {value!r}")


def to_canonical(value, dimension: str) -> float:
    """Return ``value`` as a float in the canonical unit of ``dimension``.

    A bare number is assumed to already be in the canonical unit. A quantity with
    an explicit unit is converted; a dimensional mismatch fails closed.
    """
    if dimension not in CANONICAL:
        raise UnitError(f"unknown dimension {dimension!r}")
    canon = CANONICAL[dimension]
    q = _as_quantity(value)

    # bare number -> already canonical
    if q.dimensionless and not isinstance(value, (str, dict)):
        return float(q.magnitude)

    try:
        return float(q.to(canon).magnitude)
    except pint.DimensionalityError as exc:
        raise UnitError(
            f"dimensional mismatch: {value!r} is not a {dimension} "
            f"(expected convertible to {canon}): {exc}"
        ) from None
    except Exception as exc:
        raise UnitError(f"cannot convert {value!r} to {canon}: {exc}") from None
