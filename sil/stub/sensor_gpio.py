"""Bridge between rider scripts and the firmware."""
from dataclasses import dataclass


@dataclass
class SensorGpioStub:
    pedal_torque_nm: float = 0.0
    brake_front: bool = False
    brake_rear: bool = False

    def set_pedal_torque_nm(self, nm: float) -> None:
        self.pedal_torque_nm = max(0.0, nm)

    def set_brakes(self, front: bool = False, rear: bool = False) -> None:
        self.brake_front = front
        self.brake_rear = rear
