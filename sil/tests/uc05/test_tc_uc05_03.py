"""TC-UC05-03: assist tapers to zero within 1 s above region cap.

Covers R-UC05-03. Flow id: XdLn0ledrdphP7s1.
"""
import pytest

from sil.harness import Scenario
from sil.nodes import pedal_step

REQ_ID_R_UC05_03 = "XdLn0ledrdphP7s1"
TARGET_MS = 1000.0
TOLERANCE_MS = 50.0


@pytest.mark.uc05
@pytest.mark.parametrize("region,cap_kmh", [("EU", 25.0), ("US_CLASS3", 32.0)])
def test_speed_cap_taper(harness, rider, hmi, plant, region, cap_kmh):
    hmi.set_region(region)
    rider.schedule(0, pedal_step(10.0))

    plant.force_speed_kmh(cap_kmh - 2.0)
    t_cross = 1000

    def on_tick(t_ms: int) -> None:
        if t_ms == t_cross:
            plant.force_speed_kmh(cap_kmh + 3.0)

    trace = harness.run(Scenario(
        name=f"TC-UC05-03 {region}",
        duration_ms=t_cross + 1500,
        on_tick=on_tick,
        requirements=[REQ_ID_R_UC05_03],
    ))
    after = [s for s in trace if s.t_ms >= t_cross]
    t_zero = next((s.t_ms for s in after if s.motor_cmd_nm <= 0.5), None)
    assert t_zero is not None, f"{region}: motor never tapered to zero"
    elapsed = t_zero - t_cross
    assert elapsed <= TARGET_MS + TOLERANCE_MS, \
        f"{region}: taper took {elapsed} ms (limit {TARGET_MS + TOLERANCE_MS} ms)"
