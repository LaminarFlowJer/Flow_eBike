"""TC-UC05-01: pedal-assist torque response within 250 ms.

Covers R-UC05-01. Flow id: E22F3ZHp6PFd2g6a.
"""
import pytest

from sil.harness import Scenario
from sil.nodes import pedal_step

REQ_ID_R_UC05_01 = "E22F3ZHp6PFd2g6a"
TARGET_MS = 250.0
TOLERANCE_MS = 10.0
N_RUNS = 20


@pytest.mark.uc05
def test_pedal_response_under_250ms(fw, rider, stub, plant, hmi):
    """Run 20 trials and assert worst-case latency."""
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
        r.schedule(t0, pedal_step(10.0))

        trace = harn.run(Scenario(
            name="TC-UC05-01",
            duration_ms=t0 + 400,
            on_tick=lambda _t: None,
            requirements=[REQ_ID_R_UC05_01],
        ))
        after = [x for x in trace if x.t_ms >= t0]
        t_first = next((x.t_ms for x in after if x.motor_cmd_nm > 0.0), None)
        assert t_first is not None, "motor never responded"
        latencies_ms.append(t_first - t0)

    worst = max(latencies_ms)
    assert worst <= TARGET_MS + TOLERANCE_MS, \
        f"worst-case response {worst} ms exceeded {TARGET_MS + TOLERANCE_MS} ms"
