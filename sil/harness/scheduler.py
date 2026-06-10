"""Fixed-period discrete-event scheduler."""
from typing import Iterator


class Scheduler:
    def __init__(self, period_ms: int = 1) -> None:
        self.period_ms = period_ms

    def run(self, duration_ms: int) -> Iterator[int]:
        t = 0
        while t < duration_ms:
            yield t
            t += self.period_ms
