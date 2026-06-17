"""TC-MC-10: brake-switch torque cut (single 100 ms, dual high-travel 50 ms).

Covers SW-MC-10. Flow id: Y2yuzRL6k1YBIcV8.
"""
import pytest

from sil.harness import Scenario
from sil.nodes import brake_assert, pedal_step

REQ_ID_SW_MC_10 = "Y2yuzRL6k1YBIcV8"
SINGLE_TARGET_MS = 100.0
DUAL_TARGET_MS = 50.0
TOLERANCE_MS = 5.0


def _run_brake_case(harness, rider, *, front: bool, rear: bool, label: str) -> int:
    rider.schedule(0, pedal_step(12.0))
    t_brake = 500
    rider.schedule(t_brake, brake_assert(front=front, rear=rear))
    trace = harness.run(Scenario(
        name=f"TC-MC-10 {label}",
        duration_ms=t_brake + 200,
        on_tick=lambda _t: None,
        requirements=[REQ_ID_SW_MC_10],
    ))
    after = [s for s in trace if s.t_ms >= t_brake]
    t_zero = next((s.t_ms for s in after if s.motor_cmd_nm <= 0.5), None)
    assert t_zero is not None, f"{label}: motor never reached zero"
    return t_zero - t_brake


@pytest.mark.uc05
@pytest.mark.parametrize("side", ["front", "rear"])
def test_single_brake_under_100ms(harness, rider, side):
    elapsed = _run_brake_case(
        harness, rider,
        front=(side == "front"), rear=(side == "rear"),
        label=f"single-{side}",
    )
    assert elapsed <= SINGLE_TARGET_MS + TOLERANCE_MS, \
        f"single-{side} took {elapsed} ms (limit {SINGLE_TARGET_MS + TOLERANCE_MS} ms)"


@pytest.mark.uc05
def test_dual_brake_high_travel_under_50ms(harness, rider):
    """Both brake-cutoff inputs asserted simultaneously (>= 90% travel)."""
    elapsed = _run_brake_case(
        harness, rider,
        front=True, rear=True,
        label="dual-high-travel",
    )
    assert elapsed <= DUAL_TARGET_MS + TOLERANCE_MS, \
        f"dual-brake took {elapsed} ms (limit {DUAL_TARGET_MS + TOLERANCE_MS} ms)"
