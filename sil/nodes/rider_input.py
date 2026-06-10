"""Scripted rider behaviour: schedule events at specific simulated times."""
from dataclasses import dataclass, field
from typing import Callable

from sil.stub import SensorGpioStub


@dataclass
class RiderEvent:
    t_ms: int
    action: Callable[[SensorGpioStub], None]


@dataclass
class RiderInputModel:
    stub: SensorGpioStub
    events: list[RiderEvent] = field(default_factory=list)
    idx: int = 0

    def schedule(self, t_ms: int, action: Callable[[SensorGpioStub], None]) -> None:
        self.events.append(RiderEvent(t_ms, action))
        self.events.sort(key=lambda e: e.t_ms)
        self.idx = 0

    def step(self, t_ms: int) -> None:
        while self.idx < len(self.events) and self.events[self.idx].t_ms <= t_ms:
            self.events[self.idx].action(self.stub)
            self.idx += 1


def pedal_step(nm: float) -> Callable[[SensorGpioStub], None]:
    return lambda stub: stub.set_pedal_torque_nm(nm)


def brake_assert(front: bool = True, rear: bool = False) -> Callable[[SensorGpioStub], None]:
    return lambda stub: stub.set_brakes(front=front, rear=rear)


def brake_release() -> Callable[[SensorGpioStub], None]:
    return lambda stub: stub.set_brakes(front=False, rear=False)
