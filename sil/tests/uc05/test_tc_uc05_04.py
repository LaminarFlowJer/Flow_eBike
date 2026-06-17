"""TC-UC05-04: brake assertion cuts motor torque within 100 ms.

Covers R-UC05-04 (Flow id: ke9SaX7s9gJkpiM0).
"""
import pytest

from sil.harness import Scenario
from sil.nodes import brake_assert, pedal_step

REQ_ID_R_UC05_04 = "ke9SaX7s9gJkpiM0"
TARGET_MS = 100.0
TOLERANCE_MS = 5.0


@pytest.mark.uc05
@pytest.mark.parametrize("side", ["front", "rear"])
def test_brake_cut_under_100ms(harness, rider, side):
    rider.schedule(0, pedal_step(12.0))
    t_brake = 500
    rider.schedule(t_brake, brake_assert(front=(side == "front"), rear=(side == "rear")))
    trace = harness.run(Scenario(
        name=f"TC-UC05-04 {side}",
        duration_ms=t_brake + 200,
        on_tick=lambda _t: None,
        requirements=[REQ_ID_R_UC05_04],
    ))
    after = [s for s in trace if s.t_ms >= t_brake]
    t_zero = next((s.t_ms for s in after if s.motor_cmd_nm <= 0.5), None)
    assert t_zero is not None, "motor never reached zero"
    elapsed = t_zero - t_brake
    assert elapsed <= TARGET_MS + TOLERANCE_MS, (
        f"{side}-brake cut took {elapsed} ms (limit {TARGET_MS + TOLERANCE_MS} ms)"
    )
