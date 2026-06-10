"""Longitudinal bike dynamics. Provides ground speed (SW-MC-09)."""
from dataclasses import dataclass


@dataclass
class BikeParams:
    mass_kg: float = 95.0
    wheel_radius_m: float = 0.35
    crr: float = 0.006
    cd_a: float = 0.55
    rho_air: float = 1.225
    g: float = 9.81


class VehicleDynamics:
    def __init__(self, params: BikeParams = BikeParams()) -> None:
        self.p = params
        self.v_mps: float = 0.0
        self.grade_pct: float = 0.0

    def step(self, t_ms: int, drive_torque_nm: float, dt_s: float = 1e-3) -> None:
        f_drive = drive_torque_nm / self.p.wheel_radius_m
        f_grade = self.p.mass_kg * self.p.g * (self.grade_pct / 100.0)
        f_roll = self.p.crr * self.p.mass_kg * self.p.g
        f_drag = 0.5 * self.p.rho_air * self.p.cd_a * self.v_mps * self.v_mps
        a = (f_drive - f_grade - f_roll - f_drag) / self.p.mass_kg
        self.v_mps = max(0.0, self.v_mps + a * dt_s)

    def speed_kmh(self) -> float:
        return self.v_mps * 3.6

    def force_speed_kmh(self, kmh: float) -> None:
        self.v_mps = kmh / 3.6
