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

import math
import re
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


# A quantity string is exactly: one plain decimal number, then optionally a unit.
# The number may carry a sign, a decimal point and an exponent. It may NOT carry
# spaces, thousands or decimal commas, a second decimal point, brackets, or
# arithmetic: "1 200 degC" is not 1200 and "1.2.3" is not a number. The unit part
# must start with a letter (or a degree / micro sign) and may contain digits only
# as exponents ("cm^3", "cm**3"), so a second number cannot hide inside it.
_NUMBER = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
_QUANTITY_RE = re.compile(rf"^\s*(?P<num>{_NUMBER})\s*(?P<unit>.*?)\s*$")
_UNIT_START_RE = re.compile(r"^[A-Za-z\u00b0\u00b5\u03bc]")
_UNIT_EXPONENT_RE = re.compile(r"(?:\^|\*\*)[+-]?\d+")


def _check_finite(x, original) -> None:
    if not math.isfinite(x):
        raise UnitError(f"non-finite quantity {original!r} (NaN and infinity are refused)")


def _parse_unit(unit, original) -> pint.Unit:
    """Parse a unit expression on its own. No number may hide inside it."""
    if not isinstance(unit, str) or not unit.strip():
        raise UnitError(f"unit must be a non-empty string in {original!r}")
    unit = unit.strip()
    if not _UNIT_START_RE.match(unit):
        raise UnitError(f"malformed quantity {original!r}: unit part {unit!r} does not "
                        "start with a unit name (spaces, commas or a second decimal point "
                        "inside a number are refused)")
    if re.search(r"\d", _UNIT_EXPONENT_RE.sub("", unit)):
        raise UnitError(f"malformed quantity {original!r}: unit part {unit!r} contains a "
                        "number that is not an exponent")
    try:
        u = _UREG.parse_units(unit)
    except Exception as exc:
        raise UnitError(f"unparseable unit {unit!r} in {original!r}: {exc}") from None
    return u


def _as_quantity(value) -> pint.Quantity:
    """Build a pint Quantity from number | str | {'value','unit'}; else UnitError.

    Fails closed: NaN and infinity, malformed number strings, and unit strings that
    hide a second number are refused with a named reason.
    """
    if isinstance(value, bool):
        raise UnitError(f"boolean is not a quantity: {value!r}")
    if isinstance(value, (int, float)):
        _check_finite(float(value), value)
        return _UREG.Quantity(value)  # dimensionless; caller supplies dimension
    if isinstance(value, str):
        m = _QUANTITY_RE.match(value)
        if m is None:
            raise UnitError(f"malformed quantity {value!r}: expected a plain decimal "
                            "number followed by an optional unit")
        num = float(m.group("num"))
        _check_finite(num, value)
        unit_text = m.group("unit")
        if not unit_text:
            return _UREG.Quantity(num)
        try:
            return _UREG.Quantity(num, _parse_unit(unit_text, value))
        except UnitError:
            raise
        except Exception as exc:
            raise UnitError(f"unparseable quantity {value!r}: {exc}") from None
    if isinstance(value, dict):
        if "value" not in value or "unit" not in value:
            raise UnitError(f"quantity mapping needs 'value' and 'unit': {value!r}")
        v = value["value"]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise UnitError(f"quantity mapping 'value' must be a number: {value!r}")
        _check_finite(float(v), value)
        try:
            return _UREG.Quantity(v, _parse_unit(value["unit"], value))
        except UnitError:
            raise
        except Exception as exc:
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
        out = float(q.to(canon).magnitude)
    except pint.DimensionalityError as exc:
        raise UnitError(
            f"dimensional mismatch: {value!r} is not a {dimension} "
            f"(expected convertible to {canon}): {exc}"
        ) from None
    except Exception as exc:
        raise UnitError(f"cannot convert {value!r} to {canon}: {exc}") from None
    _check_finite(out, value)
    return out
