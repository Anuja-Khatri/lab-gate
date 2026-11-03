"""P2.4 taint test (pattern from refs no_text_channel_test.py).

Inject a unique sentinel into every free-text field of every action in 1,000
generated plans; assert the verdict is byte-identical to the sentinel-free run and
the sentinel never appears in any checker input or output. Plus a static check
that gate/checker/ and gate/verdict.py never reference the quarantined field names.

The decision entrypoint is gate.verdict.decide; it depends only on the quarantined
(free-text-stripped) plan, so Phase 4's checker inherits this property unchanged.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from gate.boundary.quarantine import FREE_TEXT_FIELDS
from gate.verdict import boundary_decision, decide, plan_fingerprint
from tests.planfactory import inject_sentinel, random_valid_plan

SENTINEL = "ZZ_INJECTED_SENTINEL_ZZ"
GATE_DIR = Path(__file__).resolve().parent.parent / "gate"
N_PLANS = 1000


def test_taint_1000_plans_verdict_invariant_and_no_leak():
    rng = random.Random(42)
    for i in range(N_PLANS):
        plan = random_valid_plan(rng)
        tainted = inject_sentinel(plan, SENTINEL)

        clean_v = decide(plan)
        taint_v = decide(tainted)

        # (i) verdict byte-identical (public view, which excludes quarantined text)
        clean_pub = json.dumps(clean_v.to_public(), sort_keys=True)
        taint_pub = json.dumps(taint_v.to_public(), sort_keys=True)
        assert clean_pub == taint_pub, f"plan {i}: verdict changed under tainting"

        # (ii) sentinel never appears in the public verdict
        assert SENTINEL not in clean_pub and SENTINEL not in taint_pub

        # (iii) sentinel never appears in the typed plan fingerprint (checker input)
        _, _ = boundary_decision(plan)
        parsed_clean, _ = boundary_decision(plan)
        parsed_taint, _ = boundary_decision(tainted)
        assert SENTINEL not in plan_fingerprint(parsed_clean)
        assert SENTINEL not in plan_fingerprint(parsed_taint)
        assert plan_fingerprint(parsed_clean) == plan_fingerprint(parsed_taint)

        # (iv) the sentinel WAS captured into quarantined text (seen, set aside)
        assert any(SENTINEL in str(v) for v in taint_v.quarantined_text.values()), (
            f"plan {i}: sentinel was dropped instead of quarantined"
        )


def test_static_no_reference_to_free_text_fields():
    """gate/checker/*.py and gate/verdict.py must never name a free-text field.

    quarantine.py is the sole module allowed to name them (it defines the list).
    """
    offenders = []
    targets = list((GATE_DIR / "checker").glob("*.py")) + [GATE_DIR / "verdict.py"]
    # also scan schemas.py and units.py (decision-path modules)
    targets += [GATE_DIR / "boundary" / "schemas.py", GATE_DIR / "boundary" / "units.py"]
    for path in targets:
        if not path.exists():
            continue
        src = path.read_text()
        for field in FREE_TEXT_FIELDS:
            if re.search(rf"\b{re.escape(field)}\b", src):
                offenders.append(f"{path.name}: references {field!r}")
    assert not offenders, "decision-path modules reference quarantined fields: " + str(offenders)
