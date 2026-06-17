"""SIL harness: orchestrates firmware + plant + nodes for one scenario."""
from dataclasses import dataclass, field
from typing import Callable

from sil.firmware.mc import MotorControllerFW

from .scheduler import Scheduler


@dataclass
class Scenario:
    name: str
    duration_ms: int
    on_tick: Callable[[int], None]
    requirements: list[str] = field(default_factory=list)


@dataclass
class TraceSample:
    t_ms: int
    motor_cmd_nm: float
    pedal_nm: float
    brake: bool


class Harness:
    def __init__(self, fw: MotorControllerFW, rider, stub, plant=None, hmi=None) -> None:
        self.fw = fw
        self.rider = rider
        self.stub = stub
        self.plant = plant
        self.hmi = hmi
        self.scheduler = Scheduler(period_ms=1)
        self.trace: list[TraceSample] = []

    def run(self, scenario: Scenario) -> list[TraceSample]:
        self.trace.clear()
        for t_ms in self.scheduler.run(scenario.duration_ms):
            self.rider.step(t_ms)
            if self.hmi is not None:
                self.hmi.step(t_ms)
            scenario.on_tick(t_ms)
            pedal = self.stub.pedal_torque_nm
            brake = self.stub.brake_front or self.stub.brake_rear
            speed = self.plant.speed_kmh() if self.plant is not None else 0.0
            region_cap = self.hmi.region_cap_kmh if self.hmi is not None else 32.0
            assist = self.hmi.assist_level if self.hmi is not None else 2
            cmd = self.fw.tick(
                pedal_nm=pedal, brake=brake, speed_kmh=speed,
                region_cap_kmh=region_cap, assist_level=assist,
            )
            if self.plant is not None:
                self.plant.step(t_ms, cmd)
            self.trace.append(TraceSample(t_ms, cmd, pedal, brake))
        return self.trace
