# ebike-mc-sil

Software-in-the-loop (SIL) verification environment for the e-bike Motor Controller (MC) ECU.

This repo executes the UC-05 *Ride with Pedal Assist* verification plan against a pure-Python port of the v1 Teensy MC firmware. No hardware required.

## Quick start

```
pip install -e .[dev]
pytest -m uc05
pytest tests/uc05/test_tc_uc05_04.py -v
```

## Layout

| Path | Purpose |
|---|---|
| `firmware/mc/` | Python port of the MC firmware |
| `sil/harness/` | scheduler, runner, Flow reporter |
| `sil/plant/` | motor + drivetrain, vehicle dynamics |
| `sil/stub/` | sensor & GPIO stub |
| `sil/nodes/` | rider input, simulated HMI |
| `tests/uc05/` | one pytest module per UC-05 test case |

## Results writeback

On green CI on `main`, `sil/harness/reporter.py` updates each in-scope requirement in Flow:

- `Actual_Result` ← worst-case measured value
- `verification_status` ← `Passed` or `Failed`
