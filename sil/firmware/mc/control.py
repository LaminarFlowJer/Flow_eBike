"""Assist control: cut-in hysteresis, gain, ramp, decay, speed-cap taper."""
import math

from .config import (
    ASSIST_GAINS,
    LOOP_HZ,
    MOTOR_TORQUE_CAP_NM,
    OUTPUT_RAMP_NM_PER_S,
    PEDAL_STOP_DECAY_TARGET_NM,
    PEDAL_STOP_DECAY_TAU_MS,
    PEDAL_STOP_DETECT_MS,
    SPEED_CAP_TAPER_DURATION_MS,
    TORQUE_CUT_IN_NM,
    TORQUE_CUT_OUT_NM,
)


class AssistControl:
    def __init__(self) -> None:
        self.pedal_active = False
        self.pedal_last_above_cut_ms = 0
        self.taper_start_ms: int | None = None
        self.taper_start_torque_nm = 0.0

    def _update_pedal_active(self, pedal_nm: float, now_ms: int) -> None:
        if not self.pedal_active and pedal_nm >= TORQUE_CUT_IN_NM:
            self.pedal_active = True
        elif self.pedal_active and pedal_nm < TORQUE_CUT_OUT_NM:
            self.pedal_active = False
        if self.pedal_active:
            self.pedal_last_above_cut_ms = now_ms

    def _assist_setpoint(self, pedal_nm: float, assist_level: int) -> float:
        if not self.pedal_active:
            return 0.0
        gain = ASSIST_GAINS[max(0, min(len(ASSIST_GAINS) - 1, assist_level))]
        return min(pedal_nm * gain, MOTOR_TORQUE_CAP_NM)

    @staticmethod
    def _ramp(current: float, target: float) -> float:
        max_step = OUTPUT_RAMP_NM_PER_S / LOOP_HZ
        delta = target - current
        delta = max(-max_step, min(max_step, delta))
        return current + delta

    def _decay(self, current: float, now_ms: int) -> float:
        if self.pedal_active:
            return current
        if (now_ms - self.pedal_last_above_cut_ms) < PEDAL_STOP_DETECT_MS:
            return current
        dt_ms = 1000.0 / LOOP_HZ
        factor = math.exp(-dt_ms / PEDAL_STOP_DECAY_TAU_MS)
        nxt = current * factor
        if nxt < PEDAL_STOP_DECAY_TARGET_NM * 0.5:
            nxt = 0.0
        return nxt

    def _apply_taper(self, current_cmd: float, speed_kmh: float,
                     region_cap_kmh: float, now_ms: int) -> float:
        if speed_kmh > region_cap_kmh:
            if self.taper_start_ms is None:
                self.taper_start_ms = now_ms
                self.taper_start_torque_nm = current_cmd
            elapsed = now_ms - self.taper_start_ms
            if elapsed >= SPEED_CAP_TAPER_DURATION_MS:
                return 0.0
            frac = 1.0 - (elapsed / SPEED_CAP_TAPER_DURATION_MS)
            return self.taper_start_torque_nm * frac
        self.taper_start_ms = None
        return current_cmd

    def step(self, *, pedal_nm: float, speed_kmh: float, region_cap_kmh: float,
             assist_level: int, current_cmd: float, now_ms: int) -> float:
        self._update_pedal_active(pedal_nm, now_ms)
        target = self._assist_setpoint(pedal_nm, assist_level)
        commanded = self._ramp(current_cmd, target)
        commanded = self._decay(commanded, now_ms)
        commanded = self._apply_taper(commanded, speed_kmh, region_cap_kmh, now_ms)
        return commanded
