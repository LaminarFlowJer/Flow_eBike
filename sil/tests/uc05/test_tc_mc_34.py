"""TC-MC-34: torque-sensor sample rate >= 1 kHz.

Covers SW-MC-34. Flow id: PwGG8mw9hUoymJmW.
"""
import pytest

from sil.harness import Scenario
from sil.nodes import pedal_step

REQ_ID_SW_MC_34 = "PwGG8mw9hUoymJmW"
MIN_RATE_HZ = 1000
MAX_GAP_MS = 1


@pytest.mark.uc05
def test_torque_sample_rate(harness, rider):
    rider.schedule(0, pedal_step(8.0))
    trace = harness.run(Scenario(
        name="TC-MC-34",
        duration_ms=1000,
        on_tick=lambda _t: None,
        requirements=[REQ_ID_SW_MC_34],
    ))
    timestamps = sorted({s.t_ms for s in trace})
    n_samples = len(timestamps)
    rate_hz = n_samples / 1.0
    max_gap = max(b - a for a, b in zip(timestamps, timestamps[1:]))
    assert rate_hz >= MIN_RATE_HZ, f"sample rate {rate_hz} Hz < {MIN_RATE_HZ} Hz"
    assert max_gap <= MAX_GAP_MS, f"max gap {max_gap} ms > {MAX_GAP_MS} ms"
