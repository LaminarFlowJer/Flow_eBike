"""Minimal motor + drivetrain model."""
from dataclasses import dataclass


@dataclass
class MotorParams:
    inertia_kg_m2: float = 0.012
    viscous_friction: float = 0.005


class MotorDrivetrain:
    def __init__(self, params: MotorParams = MotorParams()) -> None:
        self.p = params
        self.omega_rad_s: float = 0.0
        self.torque_nm: float = 0.0

    def step(self, t_ms: int, commanded_nm: float, dt_s: float = 1e-3) -> None:
        self.torque_nm += (commanded_nm - self.torque_nm) * 0.5
        accel = (self.torque_nm - self.p.viscous_friction * self.omega_rad_s) / self.p.inertia_kg_m2
        self.omega_rad_s += accel * dt_s
