"""Measure each UC-05 requirement via the SIL harness and push to Flow.

Dry run (prints only):
    python -m sil.scripts.report_to_flow

Live (writes Actual_Result to Flow):
    FLOW_API_BASE=https://backend.branch.flowengineering.com \\
    FLOW_CUSTOMER=jeremiah FLOW_API_KEY=brd_... \\
    FLOW_PROJECT_ID=9de6051a-1d54-4a84-8d93-53e8aa591aeb \\
    python -m sil.scripts.report_to_flow
"""
from sil.firmware.mc import MotorControllerFW
from sil.firmware.mc.config import ASSIST_GAINS, ASSIST_LEVEL_DEFAULT, TORQUE_CUT_IN_NM
from sil.harness import Harness, Scenario, reporter
from sil.nodes import RiderInputModel, SimulatedHmiNode, brake_assert, pedal_step
from sil.plant import VehicleDynamics
from sil.stub import SensorGpioStub


def _fresh(region: str = "US_CLASS3"):
    stub = SensorGpioStub()
    rider = RiderInputModel(stub=stub)
    hmi = SimulatedHmiNode(region=region)
    plant = VehicleDynamics()
    fw = MotorControllerFW()
    return rider, plant, Harness(fw=fw, rider=rider, stub=stub, plant=plant, hmi=hmi)


def brake_cut_ms(front: bool, rear: bool) -> int:
    rider, _, harness = _fresh()
    rider.schedule(0, pedal_step(12.0))
    t_brake = 500
    rider.schedule(t_brake, brake_assert(front=front, rear=rear))
    trace = harness.run(Scenario("brake", t_brake + 200, lambda _t: None))
    after = [s for s in trace if s.t_ms >= t_brake]
    return next(s.t_ms for s in after if s.motor_cmd_nm <= 0.5) - t_brake


def _rise_time_ms(trace, t0: int, pedal_nm: float) -> int:
    expected = pedal_nm * ASSIST_GAINS[ASSIST_LEVEL_DEFAULT]
    threshold = 0.90 * expected
    after = [s for s in trace if s.t_ms >= t0]
    return next(s.t_ms for s in after if s.motor_cmd_nm >= threshold) - t0


def rise_time_ms(t0: int = 500) -> int:
    rider, _, harness = _fresh()
    rider.schedule(0, pedal_step(4.0))
    rider.schedule(t0, pedal_step(10.0))
    trace = harness.run(Scenario("pedal", t0 + 1500, lambda _t: None))
    return _rise_time_ms(trace, t0, 10.0)


def worstcase_rise_ms(n_runs: int = 20) -> int:
    worst = 0
    for _ in range(n_runs):
        rider, _, harness = _fresh()
        rider.schedule(0, pedal_step(0.0))
        t0 = 300
        rider.schedule(t0, pedal_step(10.0))
        trace = harness.run(Scenario("pedal", t0 + 700, lambda _t: None))
        worst = max(worst, _rise_time_ms(trace, t0, 10.0))
    return worst


def measured_cut_in_nm() -> float:
    """Lowest pedal torque (Nm) at which assist engages."""
    rider, _, harness = _fresh()
    for ms in range(0, 801, 10):
        rider.schedule(ms, pedal_step(ms * 0.01))
    trace = harness.run(Scenario("sweep", 1000, lambda _t: None))
    engaged = next(s for s in trace if s.motor_cmd_nm > 0.0)
    return round(engaged.pedal_nm, 1)


def taper_s(region: str, cap_kmh: float) -> float:
    rider, plant, harness = _fresh(region)
    rider.schedule(0, pedal_step(10.0))
    plant.force_speed_kmh(cap_kmh - 2.0)
    t_cross = 1000

    def on_tick(t_ms: int) -> None:
        if t_ms == t_cross:
            plant.force_speed_kmh(cap_kmh + 3.0)

    trace = harness.run(Scenario("taper", t_cross + 1500, on_tick))
    after = [s for s in trace if s.t_ms >= t_cross]
    return (next(s.t_ms for s in after if s.motor_cmd_nm <= 0.5) - t_cross) / 1000.0


def rate_hz(window_ms: int = 1000) -> float:
    rider, _, harness = _fresh()
    rider.schedule(0, pedal_step(8.0))
    trace = harness.run(Scenario("rate", window_ms, lambda _t: None))
    return len({s.t_ms for s in trace}) / (window_ms / 1000.0)


def collect():
    assert measured_cut_in_nm() == TORQUE_CUT_IN_NM  # sanity: 5 Nm
    return [
        ("ke9SaX7s9gJkpiM0", "R-UC05-04 brake cut (ms)",
         max(brake_cut_ms(True, False), brake_cut_ms(False, True))),
        ("0CeTDZquNLJPpeI7", "SW-MC-02 rise time (ms)", rise_time_ms()),
        ("jwPPVc8Hmp0JRohP", "SW-MC-30 cut-in (Nm)", measured_cut_in_nm()),
        ("E22F3ZHp6PFd2g6a", "R-UC05-01 rise time (ms)", worstcase_rise_ms()),
        ("aMDD1QmMOG0DD2YA", "R-UC05-02 publish rate (Hz)", rate_hz()),
        ("XdLn0ledrdphP7s1", "R-UC05-03 taper (s)",
         max(taper_s("EU", 25.0), taper_s("US_CLASS3", 32.0))),
        ("xopDctbKzqvGQz1o", "SW-MC-09 taper (s)", taper_s("US_CLASS3", 32.0)),
        ("Y2yuzRL6k1YBIcV8", "SW-MC-10 dual-brake cut (ms)", brake_cut_ms(True, True)),
        ("PwGG8mw9hUoymJmW", "SW-MC-34 sample rate (kHz)", rate_hz() / 1000.0),
    ]


def main() -> None:
    results = collect()
    for req_id, label, measured in results:
        print(f"  {label:34s} -> {measured}")
    reporter.push_results([(req_id, m) for req_id, _, m in results])


if __name__ == "__main__":
    main()
