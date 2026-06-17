"""TC-UC05-02: pedal-torque publish rate >= 10 Hz.

Covers R-UC05-02. Flow id: aMDD1QmMOG0DD2YA.
"""
import pytest

from sil.harness import Scenario
from sil.nodes import pedal_step

REQ_ID_R_UC05_02 = "aMDD1QmMOG0DD2YA"
MIN_RATE_HZ = 10
MAX_GAP_MS = 100


@pytest.mark.uc05
def test_torque_publish_rate(harness, rider):
    rider.schedule(0, pedal_step(8.0))
    trace = harness.run(Scenario(
        name="TC-UC05-02",
        duration_ms=1000,
        on_tick=lambda _t: None,
        requirements=[REQ_ID_R_UC05_02],
    ))
    timestamps = sorted({s.t_ms for s in trace})
    n_samples = len(timestamps)
    rate_hz = n_samples / 1.0
    max_gap = max(b - a for a, b in zip(timestamps, timestamps[1:]))
    assert rate_hz >= MIN_RATE_HZ, f"publish rate {rate_hz} Hz < {MIN_RATE_HZ} Hz"
    assert max_gap <= MAX_GAP_MS, f"max gap {max_gap} ms > {MAX_GAP_MS} ms"
