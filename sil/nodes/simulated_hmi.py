"""Simulated HMI: assist level + region cap."""
from sil.firmware.mc.config import ASSIST_LEVEL_DEFAULT, REGION_CAP_KMH


class SimulatedHmiNode:
    def __init__(self, assist_level: int = ASSIST_LEVEL_DEFAULT, region: str = "US_CLASS3") -> None:
        self.assist_level = assist_level
        self.region = region

    @property
    def region_cap_kmh(self) -> float:
        return REGION_CAP_KMH[self.region]

    def set_assist(self, level: int) -> None:
        self.assist_level = max(0, min(4, level))

    def set_region(self, region: str) -> None:
        assert region in REGION_CAP_KMH
        self.region = region

    def step(self, t_ms: int) -> None:
        return
