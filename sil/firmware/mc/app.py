"""MC firmware top-level. One tick = 1 ms of simulated time."""
from .config import LOOP_PERIOD_MS
from .control import AssistControl
from .safety import SafetyMonitor


class MotorControllerFW:
    def __init__(self) -> None:
        self.control = AssistControl()
        self.safety = SafetyMonitor()
        self.motor_cmd_nm: float = 0.0
        self.t_ms: int = 0

    def tick(self, *, pedal_nm: float, brake: bool, speed_kmh: float = 0.0,
             region_cap_kmh: float = 32.0, assist_level: int = 2) -> float:
        if self.safety.brake_cut(brake):
            self.motor_cmd_nm = 0.0
        else:
            self.motor_cmd_nm = self.control.step(
                pedal_nm=pedal_nm, speed_kmh=speed_kmh,
                region_cap_kmh=region_cap_kmh, assist_level=assist_level,
                current_cmd=self.motor_cmd_nm, now_ms=self.t_ms,
            )
        self.t_ms += LOOP_PERIOD_MS
        return self.motor_cmd_nm
