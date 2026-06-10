"""TC-MC-09: linear speed-cap taper.

Covers SW-MC-09. Flow id: xopDctbKzqvGQz1o.
Stricter than TC-UC05-03: also checks linearity.
"""
import pytest

from sil.harness import Scenario
from sil.nodes import pedal_step

REQ_ID_SW_MC_09 = "xopDctbKzqvGQz1o"
TARGET_MS = 1000.0
TOLERANCE_MS = 50.0
LINEARITY_TOLERANCE_PCT = 10.0


@pytest.mark.uc05
def test_speed_cap_linear_taper(harness, rider, hmi, plant):
    hmi.set_region("US_CLASS3")
    rider.schedule(0, pedal_step(12.0))
    plant.force_speed_kmh(30.0)   # below 32 km/h cap
    t_cross = 1000

    def on_tick(t_ms: int) -> None:
        if t_ms == t_cross:
            plant.force_speed_kmh(35.0)  # past cap

    trace = harness.run(Scenario(
        name="TC-MC-09",
        duration_ms=t_cross + 1500,
        on_tick=on_tick,
        requirements=[REQ_ID_SW_MC_09],
    ))

    after = [s for s in trace if s.t_ms >= t_cross]
    t_zero = next((s.t_ms for s in after if s.motor_cmd_nm <= 0.5), None)
    assert t_zero is not None, "torque never tapered to zero"
    elapsed = t_zero - t_cross
    assert elapsed <= TARGET_MS + TOLERANCE_MS, \
        f"taper took {elapsed} ms (limit {TARGET_MS + TOLERANCE_MS} ms)"

    # Linearity check: torque should drop ~linearly over the taper region.
    taper = [s for s in after if t_cross <= s.t_ms <= t_zero]
    start_torque = taper[0].motor_cmd_nm
    if start_torque > 0.0:
        # Predicted torque under perfect linear taper
        predicted = [
            start_torque * (1.0 - (s.t_ms - t_cross) / (t_zero - t_cross))
            for s in taper
        ]
        deviations = [
            abs(s.motor_cmd_nm - pred) for s, pred in zip(taper, predicted)
        ]
        rms = (sum(d * d for d in deviations) / len(deviations)) ** 0.5
        rms_pct = rms / start_torque * 100.0
        assert rms_pct <= LINEARITY_TOLERANCE_PCT, \
            f"linearity deviation {rms_pct:.1f}% > {LINEARITY_TOLERANCE_PCT}%"
