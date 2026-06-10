"""TC-UC05-01: pedal-assist torque response within 250 ms.

Covers R-UC05-01. Flow id: E22F3ZHp6PFd2g6a.

Response is measured as *rise time* — the time for commanded motor torque to
reach 90% of its steady-state target after pedal torque crosses the cut-in
threshold. (Measuring "first non-zero" instead is meaningless here: the output
ramp produces 0.04 Nm on the very first tick, so it would always report ~0 ms
and never constrain the ramp rate the rider actually feels.)
"""
import pytest

from firmware.mc.config import ASSIST_GAINS, ASSIST_LEVEL_DEFAULT
from sil.harness import Scenario
from sil.nodes import pedal_step

REQ_ID_R_UC05_01 = "E22F3ZHp6PFd2g6a"
TARGET_MS = 250.0
TOLERANCE_MS = 10.0
N_RUNS = 20

PEDAL_NM = 10.0
EXPECTED_STEADY_NM = PEDAL_NM * ASSIST_GAINS[ASSIST_LEVEL_DEFAULT]  # 15 Nm
RISE_THRESHOLD_NM = 0.90 * EXPECTED_STEADY_NM                       # 13.5 Nm


@pytest.mark.uc05
def test_pedal_response_under_250ms(fw, rider, stub, plant, hmi):
    """Run 20 trials and assert worst-case rise time to 90% of target."""
    from sil.harness import Harness

    latencies_ms: list[int] = []
    for _ in range(N_RUNS):
        # fresh fixtures per run
        from firmware.mc import MotorControllerFW
        from sil.nodes import RiderInputModel, SimulatedHmiNode
        from sil.plant import VehicleDynamics
        from sil.stub import SensorGpioStub

        s = SensorGpioStub()
        r = RiderInputModel(stub=s)
        h = SimulatedHmiNode()
        p = VehicleDynamics()
        f = MotorControllerFW()
        harn = Harness(fw=f, rider=r, stub=s, plant=p, hmi=h)

        r.schedule(0, pedal_step(0.0))
        t0 = 300
        r.schedule(t0, pedal_step(PEDAL_NM))

        trace = harn.run(Scenario(
            name="TC-UC05-01",
            duration_ms=t0 + 700,
            on_tick=lambda _t: None,
            requirements=[REQ_ID_R_UC05_01],
        ))
        after = [x for x in trace if x.t_ms >= t0]
        t_rise = next((x.t_ms for x in after if x.motor_cmd_nm >= RISE_THRESHOLD_NM), None)
        assert t_rise is not None, "motor never reached 90% of target"
        latencies_ms.append(t_rise - t0)

    worst = max(latencies_ms)
    assert worst <= TARGET_MS + TOLERANCE_MS, \
        f"worst-case rise time {worst} ms exceeded {TARGET_MS + TOLERANCE_MS} ms"
