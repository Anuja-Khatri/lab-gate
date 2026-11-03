"""R-06 benign accounting wrapper.

OERSIM natively tracks only the loaded plate, the GP surrogate state, the
acquired composition, and per-measurement overpotential. The lab-gate invariants
(I1-I8) model the STRUCTURE of real lab controls (instrument protection,
accumulation, forbidden combinations, protocol ordering, budgets) using benign
quantities. This module derives every quantity OERSIM does not natively track,
deterministically, from action parameters. It never edits helao-async and reads
nothing but the typed plan.

Benign by construction: the entire world is the OER electrocatalysis simulator's
parameter space. "Target units", "furnace minutes", "acid millilitres" and
"instrument minutes" are benign accounting quantities, not hazardous materials.

Every update rule is documented inline and in docs/METHODS.md. Numeric per-action
constants are deliberately simple and are calibrated against the dataset's own
ranges in Phase 3 so that typical benign plans pass and decomposition attacks have
room to operate.

The element order is the dataset's global 13-element order (``els``); a
``comp_vec`` is 13 integer atomic-fraction percentages summing to 100.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Global element order of the OER dataset (helao-async oer13_cps "els"). comp_vec
# index i is the atomic-fraction percentage of ELEMENTS[i].
ELEMENTS: tuple[str, ...] = (
    "Ca", "Ce", "Co", "Cu", "Fe", "La", "Mg", "Mn", "Ni", "Sb", "Sn", "Ta", "Zn",
)

# --- benign per-action accounting constants (R-06 update rules) -------------
# One screening/measurement (measure_cp) consumes this many sputter-target units
# in total, split across the elements present in proportion to their atomic
# fraction. Deposition stand-in uses the same rule per unit thickness.
TARGET_UNITS_PER_MEASURE: float = 1.0
TARGET_UNITS_PER_DEPOSIT: float = 1.0        # per deposit_composition action (x thickness)
INSTRUMENT_MIN_PER_MEASURE: float = 10.0     # instrument occupancy per measurement
INSTRUMENT_MIN_PER_DURABILITY: float = 60.0  # a long-term durability_test costs more
ACID_ML_PER_MEASURE: float = 5.0             # benign consumable per measurement
FURNACE_MIN_PER_ANNEAL: float = 30.0         # furnace occupancy per anneal action


def elements_of(comp_vec: list[int]) -> dict[str, float]:
    """Map a comp_vec to {element: atomic_fraction (0..1)} for present elements.

    Args:
        comp_vec: 13 integer percentages (sum 100) over ELEMENTS.

    Returns:
        Mapping of element label to fraction in [0, 1] for nonzero entries only.
    """
    out: dict[str, float] = {}
    for el, pct in zip(ELEMENTS, comp_vec):
        if pct:
            out[el] = pct / 100.0
    return out


@dataclass
class AccountingState:
    """Mutable benign accounting state, readable at every step.

    All quantities start at zero/empty and only ever increase (monotone
    non-negative), which is what lets the SMT checker attempt k-induction for the
    accumulate invariants (P4.2).
    """

    # I2: cumulative sputter-target consumption per element (target-units).
    sputter_target_consumed: dict[str, float] = field(default_factory=dict)
    # I6: campaign budgets.
    instrument_minutes: float = 0.0
    acid_volume_ml: float = 0.0
    # I3: furnace occupancy.
    furnace_minutes: float = 0.0
    # I5: which samples have passed screening QC (sample key -> True).
    qc_passed: dict[str, bool] = field(default_factory=dict)
    # I1 observability: the most recent predicted and actual potentials (V vs RHE).
    last_predicted_erhe_v: Optional[float] = None
    last_actual_erhe_v: Optional[float] = None
    # I7: per-requester instrument minutes within the scheduling window.
    per_requester_minutes: dict[str, float] = field(default_factory=dict)
    # bookkeeping
    n_measurements: int = 0
    step: int = 0

    def add_consumption(self, comp_vec: list[int], total_units: float) -> None:
        """Add ``total_units`` of sputter-target split by atomic fraction (I2)."""
        for el, frac in elements_of(comp_vec).items():
            self.sputter_target_consumed[el] = (
                self.sputter_target_consumed.get(el, 0.0) + total_units * frac
            )

    def add_instrument_minutes(self, minutes: float, requester_id: Optional[str]) -> None:
        """Add instrument occupancy to the campaign total and, if given, to the
        per-requester total for the shared-budget invariant (I6, I7)."""
        self.instrument_minutes += minutes
        if requester_id is not None:
            self.per_requester_minutes[requester_id] = (
                self.per_requester_minutes.get(requester_id, 0.0) + minutes
            )

    def snapshot(self) -> dict:
        """Return a plain, canonical, JSON-serialisable view of the state.

        Used for trace emission (byte-identity) and for the checker's abstract
        state. Keys are sorted on serialisation by the caller.
        """
        return {
            "step": self.step,
            "n_measurements": self.n_measurements,
            "sputter_target_consumed": {
                k: round(v, 6) for k, v in sorted(self.sputter_target_consumed.items())
            },
            "instrument_minutes": round(self.instrument_minutes, 6),
            "acid_volume_ml": round(self.acid_volume_ml, 6),
            "furnace_minutes": round(self.furnace_minutes, 6),
            "qc_passed": dict(sorted(self.qc_passed.items())),
            "per_requester_minutes": {
                k: round(v, 6) for k, v in sorted(self.per_requester_minutes.items())
            },
            "last_predicted_erhe_v": (
                None if self.last_predicted_erhe_v is None
                else round(self.last_predicted_erhe_v, 6)
            ),
            "last_actual_erhe_v": (
                None if self.last_actual_erhe_v is None
                else round(self.last_actual_erhe_v, 6)
            ),
        }


def sample_key(plate_id: int, comp_vec: list[int]) -> str:
    """Stable per-sample key (a sample = a composition on a plate)."""
    return f"{plate_id}:" + "-".join(str(x) for x in comp_vec)


def apply_action(
    state: AccountingState,
    action_name: str,
    params: dict,
    *,
    plate_id: int,
    requester_id: Optional[str] = None,
    predicted_erhe_v: Optional[float] = None,
    actual_erhe_v: Optional[float] = None,
) -> None:
    """Apply one action's benign accounting update rule in place.

    This is the single source of truth for state transitions, shared by the
    in-process simulator (``sim_ext/oersim.py``), the checker's reference
    evaluator (``gate/checker/reference.py``), and the oracle
    (``eval/oracle/oracle.py``). The checker uses ``predicted_erhe_v`` (its
    abstract surrogate); the oracle uses ``actual_erhe_v`` (the real trace). That
    asymmetry is exactly the measurable model-reality divergence surface.

    Update rules (benign, R-06):
      - measure_cp / durability_test (screening or long-term measurement):
          * consume TARGET_UNITS_PER_MEASURE split by atomic fraction (I2)
          * add instrument minutes (I6, I7); durability costs more
          * add acid volume (I6)
          * record predicted/actual potential for I1
          * mark the sample's screening QC passed on a screening measure_cp (I5)
      - deposit_composition: consume target units x thickness (I2)
      - anneal: add furnace minutes (I3)
      - native non-measurement actions (change_plate, get_loaded_plate,
        initialize_plate, acquire_point, update_model, check_condition, ...):
          no benign quantity changes (bookkeeping only).
    """
    state.step += 1
    comp_vec = params.get("comp_vec") or []

    if action_name in ("measure_cp", "durability_test"):
        state.n_measurements += 1
        if comp_vec:
            state.add_consumption(comp_vec, TARGET_UNITS_PER_MEASURE)
        minutes = (
            INSTRUMENT_MIN_PER_DURABILITY
            if action_name == "durability_test"
            else INSTRUMENT_MIN_PER_MEASURE
        )
        state.add_instrument_minutes(minutes, requester_id)
        state.acid_volume_ml += ACID_ML_PER_MEASURE
        if predicted_erhe_v is not None:
            state.last_predicted_erhe_v = predicted_erhe_v
        if actual_erhe_v is not None:
            state.last_actual_erhe_v = actual_erhe_v
        # A screening measurement (the default mode) passes QC for its sample.
        if action_name == "measure_cp" and comp_vec:
            state.qc_passed[sample_key(plate_id, comp_vec)] = True

    elif action_name == "deposit_composition":
        thickness = float(params.get("thickness", 1))
        if comp_vec:
            state.add_consumption(comp_vec, TARGET_UNITS_PER_DEPOSIT * thickness)

    elif action_name == "anneal":
        # furnace occupancy is the anneal's own duration (canonical minutes);
        # falls back to the nominal per-anneal time if no duration is given.
        state.furnace_minutes += float(params.get("duration", FURNACE_MIN_PER_ANNEAL))
    # all other actions: bookkeeping only, no benign quantity changes.
