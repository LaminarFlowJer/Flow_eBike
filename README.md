# Flow_eBike

Monorepo for the e-bike program. Two top-level domains:

- **`ebike/`** — on-target product code (firmware that runs on real hardware).
- **`sil/`** — Software-in-the-Loop verification environment that runs on a host machine.

## Layout

| Path | Purpose |
|---|---|
| `ebike/firmware/mc_teensy/` | v1 Teensy on-target MC firmware (Arduino sketch) |
| `sil/firmware/mc/` | Pure-Python port of the MC firmware |
| `sil/harness/` | Scheduler, runner, Flow reporter |
| `sil/plant/` | Motor + drivetrain, vehicle dynamics |
| `sil/stub/` | Sensor & GPIO stub |
| `sil/nodes/` | Rider input, simulated HMI |
| `sil/tests/uc05/` | One pytest module per UC-05 test case |
| `sil/scripts/` | Operational scripts (e.g. Flow result writeback) |

## Quick start (SIL)

```
pip install -e .[dev]
pytest -m uc05
pytest sil/tests/uc05/test_tc_uc05_04.py -v
```

## On-target firmware

The v1 Teensy MC firmware lives in `ebike/firmware/mc_teensy/`. Build with Arduino IDE + Teensyduino — see `ebike/firmware/mc_teensy/README.md`.

The Python port under `sil/firmware/mc/` mirrors that sketch module-by-module so the path back to hardware stays mechanical.

## Results writeback

On green CI on `main`, `sil/harness/reporter.py` updates each in-scope requirement in Flow:

- `Actual_Result` ← worst-case measured value
- `verification_status` is auto-computed by Flow from `Actual_Result` vs the requirement's pass/fail criteria.
