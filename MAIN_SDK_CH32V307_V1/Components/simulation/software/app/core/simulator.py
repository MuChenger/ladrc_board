import math
import random
import time
from dataclasses import dataclass

from .models import SimFeedback


@dataclass
class PlantParams:
    mass: float = 8.0
    damping: float = 2.8
    buoyancy_bias: float = 0.3
    noise_std: float = 0.005
    disturb_amp: float = 0.2
    disturb_freq_hz: float = 0.15


class DepthPlantSimulator:
    def __init__(self, params: PlantParams | None = None) -> None:
        self.params = params or PlantParams()
        self.depth = 0.0
        self.depth_rate = 0.0
        self.last_u = 0.0
        self._t = 0.0
        self._disturbance_scale = 1.0

    def reset(self, depth: float = 0.0, depth_rate: float = 0.0) -> None:
        self.depth = depth
        self.depth_rate = depth_rate
        self.last_u = 0.0
        self._t = 0.0

    def set_disturbance_scale(self, scale: float) -> None:
        self._disturbance_scale = max(0.0, float(scale))

    def step(self, dt: float, u: float) -> SimFeedback:
        dt = max(1e-4, dt)
        self._t += dt
        self.last_u = u

        disturb = (
            self.params.disturb_amp
            * self._disturbance_scale
            * math.sin(2.0 * math.pi * self.params.disturb_freq_hz * self._t)
        )
        acc = (
            (u + disturb)
            - self.params.damping * self.depth_rate
            - self.params.buoyancy_bias
        ) / max(self.params.mass, 1e-3)

        self.depth_rate += acc * dt
        self.depth += self.depth_rate * dt

        measured_depth = self.depth + random.gauss(0.0, self.params.noise_std)
        return SimFeedback(
            timestamp_ms=int(time.time() * 1000),
            depth=measured_depth,
            depth_rate=self.depth_rate,
            disturbance=disturb,
        )

