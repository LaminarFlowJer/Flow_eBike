"""Safety-critical override: brake cut."""


class SafetyMonitor:
    """R-UC05-04 / SW-MC-10: brake assertion forces zero motor torque."""

    def brake_cut(self, brake_asserted: bool) -> bool:
        return brake_asserted
