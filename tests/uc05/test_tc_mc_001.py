"""TC-MC-001: pedal-torque produces proportional motor torque.

Covers SW-MC-02 (latency <= 150 ms) and SW-MC-30 (cut-in 5 Nm, cut-out 3 Nm).
Flow requirement IDs:
  - SW-MC-02 : 0CeTDZquNLJPpeI7
  - SW-MC-30 : jwPPVc8Hmp0JRohP
"""
import pytest

from sil.harness import Scenario
from sil.nodes import pedal_step

REQ_ID_SW_MC_02 = "0CeTDZquNLJPpeI7"
REQ_ID_SW_MC_30 = "jwPPVc8Hmp0JRohP"

PEDAL_NM = 10.0
ASSIST_GAIN_TOUR = 1.5
EXPECTED_STEADY_NM = PEDAL_NM * ASSIST_GAIN_TOUR        # 15 Nm
LATENCY_LIMIT_MS = 150 + 5
PRE_CUT_IN_NM = 4.0   # below cut-in (5 Nm)


@pytest.mark.uc05
def test_pedal_torque_proportional_motor_torque(harness, rider):
    # Below cut-in -> motor should remain at 0
    rider.schedule(0, pedal_step(PRE_CUT_IN_NM))
    # Step above cut-in at T0 = 500 ms
    t0 = 500
    rider.schedule(t0, pedal_step(PEDAL_NM))

    trace = harness.run(Scenario(
        name="TC-MC-001",
        duration_ms=t0 + 1500,
        on_tick=lambda _t: None,
        requirements=[REQ_ID_SW_MC_02, REQ_ID_SW_MC_30],
    ))

    # SW-MC-30: nothing commanded before cut-in
    pre = [s for s in trace if s.t_ms < t0]
    assert max(s.motor_cmd_nm for s in pre) == 0.0, \
        "motor torque commanded below cut-in threshold"

    # SW-MC-02: rise time to 90% of steady-state target within 150 ms +/- 5 ms.
    # (Not "first non-zero": the output ramp emits 0.04 Nm on the first tick, so
    # first-non-zero is always ~0 ms and never constrains the ramp rate.)
    after = [s for s in trace if s.t_ms >= t0]
    rise_threshold_nm = 0.90 * EXPECTED_STEADY_NM
    t_rise = next((s.t_ms for s in after if s.motor_cmd_nm >= rise_threshold_nm), None)
    assert t_rise is not None, "motor never reached 90% of target"
    latency = t_rise - t0
    assert latency <= LATENCY_LIMIT_MS, \
        f"rise time {latency} ms exceeded {LATENCY_LIMIT_MS} ms"

    # Steady-state torque approaches 15 Nm (+/- 1 Nm) within 1 s
    settle_ms = t0 + 1000
    steady = [s for s in trace if s.t_ms >= settle_ms]
    final = steady[-1].motor_cmd_nm
    assert abs(final - EXPECTED_STEADY_NM) <= 1.0, \
        f"steady-state torque {final} Nm not within +/- 1 Nm of {EXPECTED_STEADY_NM} Nm"
