# MC Firmware — v1 (Teensy 4.0)

On-target Motor Controller (ECU) firmware for the e-bike.

## Scope (v1)
Two inputs (pedal torque on A0; assist level via USB-serial `L0..L4` commands as a stub for IF-CAN-HMI2MC) and one output (PWM on pin 2 as a stand-in for IF-MC-3PH).

Implements HW-MC-01/03/05/06 and SW-MC-01/02/04/06/30/31/33 (partial) /34/35.

## Build
Arduino IDE + Teensyduino. Settings:

| Setting | Value |
|---|---|
| Board | Teensy 4.0 |
| USB Type | Serial |
| CPU Speed | 600 MHz |
| Optimize | Faster |

Open `mc_fw_v1.ino` and flash. The status LED blinks at 1 Hz once Armed.

## Pin map
| Pin | Role | Interface |
|---|---|---|
| A0 (14) | Pedal torque ADC (0-3.3 V -> 0..50 Nm) | IF-MC-TORQUE |
| 2 | Motor PWM out (single-channel stand-in) | IF-MC-3PH |
| 13 | Status LED | — |
| USB serial | `Ln`/`?` commands | IF-CAN-HMI2MC (stub) |

## Verification
This sketch is the reference implementation. The pure-Python port in `sil/firmware/mc/` mirrors it module-by-module and is exercised by the UC-05 SIL suite in `sil/tests/uc05/`.

Source of truth: Flow software entity *MC FW v1 — Teensy 4.0 sketch*.
