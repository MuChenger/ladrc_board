import math
import random
import time
from dataclasses import dataclass, replace

from .models import SimFeedback


DISTURBANCE_WAVE_COMPONENTS = {
    "off": (),
    "low": (
        (0.90, 5.00, 0.0),
    ),
    "medium": (
        (1.00, 7.00, 0.0),
        (0.28, 11.00, math.pi / 6.0),
    ),
    "high": (
        (1.20, 9.00, 0.0),
        (0.55, 14.00, math.pi / 4.0),
    ),
    "extreme": (
        (1.35, 12.00, 0.0),
        (0.80, 18.00, math.pi / 4.0),
        (0.30, 26.00, math.pi / 2.0),
    ),
}


DISTURBANCE_MODE_KEYS = {"sine", "step", "drift"}


def _normalize_disturbance_level(level_key: str) -> str:
    key = str(level_key).strip().lower()
    return key if key in DISTURBANCE_WAVE_COMPONENTS else "medium"


def _normalize_disturbance_mode(mode_key: str) -> str:
    key = str(mode_key).strip().lower()
    return key if key in DISTURBANCE_MODE_KEYS else "sine"


@dataclass
class DisturbanceParams:
    amplitude_gain: float = 1.0
    frequency_gain: float = 1.0
    bias: float = 0.0


def _disturbance_wave(
    mode_key: str,
    level_key: str,
    base_amp: float,
    base_freq_hz: float,
    scale: float,
    t: float,
    params: DisturbanceParams | None = None,
) -> float:
    tuning = params if isinstance(params, DisturbanceParams) else DisturbanceParams()
    mode = _normalize_disturbance_mode(mode_key)
    components = DISTURBANCE_WAVE_COMPONENTS.get(_normalize_disturbance_level(level_key), DISTURBANCE_WAVE_COMPONENTS["medium"])
    if not components or scale <= 0.0 or base_amp <= 0.0:
        return 0.0
    effective_amp = base_amp * max(0.0, float(tuning.amplitude_gain))
    effective_freq_hz = base_freq_hz * max(0.0, float(tuning.frequency_gain))
    bias = float(tuning.bias)
    if effective_amp <= 0.0 and abs(bias) <= 1e-12:
        return 0.0
    wave = 0.0
    if mode == "step":
        step_freq_hz = max(0.08, effective_freq_hz * 0.18)
        sign = 1.0 if math.sin(2.0 * math.pi * step_freq_hz * t) >= 0.0 else -1.0
        ripple = 0.0
        for amp_mul, freq_mul, phase in components[:2]:
            ripple += 0.12 * effective_amp * scale * amp_mul * math.sin(
                2.0 * math.pi * effective_freq_hz * max(1.0, freq_mul * 0.35) * t + phase
            )
        step_gain = 1.0 + 0.18 * max(0, len(components) - 1)
        wave = effective_amp * scale * step_gain * sign + ripple
    elif mode == "drift":
        slow_freq_hz = max(0.03, effective_freq_hz * 0.10)
        carrier = math.tanh(2.4 * math.sin(2.0 * math.pi * slow_freq_hz * t))
        wave = effective_amp * scale * 0.92 * carrier
        for amp_mul, freq_mul, phase in components[:2]:
            wave += 0.10 * effective_amp * scale * amp_mul * math.sin(
                2.0 * math.pi * effective_freq_hz * max(0.6, freq_mul * 0.18) * t + phase
            )
    else:
        for amp_mul, freq_mul, phase in components:
            if effective_amp <= 0.0 or effective_freq_hz <= 0.0:
                break
            wave += (
                effective_amp
                * scale
                * amp_mul
                * math.sin(2.0 * math.pi * effective_freq_hz * freq_mul * t + phase)
            )
    return wave + bias * scale


class DisturbanceSignalGenerator:
    def __init__(self, base_amp: float, base_freq_hz: float) -> None:
        self.base_amp = max(0.0, float(base_amp))
        self.base_freq_hz = max(0.0, float(base_freq_hz))
        self._params = DisturbanceParams()
        self._mode_key = "sine"
        self._level_key = "medium"
        self._scale = 1.0
        self._t = 0.0
        self._current = 0.0

    def set_disturbance_mode(self, mode_key: str) -> None:
        self._mode_key = _normalize_disturbance_mode(mode_key)

    def set_disturbance_level(self, level_key: str, scale: float | None = None) -> None:
        self._level_key = _normalize_disturbance_level(level_key)
        if scale is not None:
            self._scale = max(0.0, float(scale))

    def set_disturbance_params(self, params: DisturbanceParams) -> None:
        self._params = DisturbanceParams(
            amplitude_gain=max(0.0, float(params.amplitude_gain)),
            frequency_gain=max(0.0, float(params.frequency_gain)),
            bias=float(params.bias),
        )

    def reset(self) -> None:
        self._t = 0.0
        self._current = 0.0

    def sample(self, dt: float) -> float:
        self._t += max(1e-4, float(dt))
        self._current = _disturbance_wave(
            self._mode_key,
            self._level_key,
            self.base_amp,
            self.base_freq_hz,
            self._scale,
            self._t,
            self._params,
        )
        return self._current

    def snapshot(self) -> float:
        return float(self._current)


@dataclass
class PlantParams:
    mass: float = 8.0
    damping: float = 2.8
    buoyancy_bias: float = 0.3
    noise_std: float = 0.005
    disturb_amp: float = 0.2
    disturb_freq_hz: float = 0.15


@dataclass
class LadrcParams:
    r: float = 20.0
    h: float = 0.02
    w0: float = 40.0
    wc: float = 2.0
    b0: float = 0.5


class LinearLadrcController:
    OUTPUT_LIMIT = 2000.0

    def __init__(self, params: LadrcParams | None = None) -> None:
        self.params = replace(params) if params is not None else LadrcParams()
        self.reset_states()

    def reset_states(self) -> None:
        self.v1 = 0.0
        self.v2 = 0.0
        self.z1 = 0.0
        self.z2 = 0.0
        self.z3 = 0.0
        self.u = 0.0

    def restore_defaults(self) -> None:
        self.params = LadrcParams()
        self.reset_states()

    def apply_params(self, params: LadrcParams) -> None:
        self.params = replace(params)

    def td(self, expect: float) -> None:
        fh = -self.params.r * self.params.r * (self.v1 - expect) - 2.0 * self.params.r * self.v2
        self.v1 += self.v2 * self.params.h
        self.v2 += fh * self.params.h

    def eso(self, feedback: float) -> None:
        beta01 = 3.0 * self.params.w0
        beta02 = 3.0 * self.params.w0 * self.params.w0
        beta03 = self.params.w0 * self.params.w0 * self.params.w0
        error = self.z1 - feedback
        self.z1 += (self.z2 - beta01 * error) * self.params.h
        self.z2 += (self.z3 - beta02 * error + self.params.b0 * self.u) * self.params.h
        self.z3 += -beta03 * error * self.params.h

    def lf(self) -> None:
        wc = self.params.wc if self.params.wc > 0.0 else (self.params.w0 / 4.0)
        self.params.wc = wc
        kp = wc * wc
        kd = 2.0 * wc
        e1 = self.v1 - self.z1
        e2 = self.v2 - self.z2
        u0 = kp * e1 + kd * e2
        self.u = (u0 - self.z3) / max(self.params.b0, 1e-6)
        self.u = max(-self.OUTPUT_LIMIT, min(self.OUTPUT_LIMIT, self.u))

    def loop(self, expect: float, feedback: float) -> None:
        self.td(expect)
        self.eso(feedback)
        self.lf()


class LadrcSimulationSession:
    MODE_TD = 0
    MODE_LOOP = 1
    MODE_IDLE = 2
    PLANT_MASS = 8.0
    PLANT_DAMPING = 2.8
    DISTURB_AMP = 0.45
    DISTURB_FREQ_HZ = 0.18

    def __init__(self, params: LadrcParams | None = None) -> None:
        self.controller = LinearLadrcController(params)
        self.init_val = 0.0
        self.expect_val = 0.0
        self.real_val = 0.0
        self.real_rate = 0.0
        self.mode = self.MODE_IDLE
        self._disturbance_params = DisturbanceParams()
        self._disturbance_mode_key = "sine"
        self._disturbance_level_key = "medium"
        self._disturbance_scale = 1.0
        self._t = 0.0
        self._disturbance = 0.0

    def restore_defaults(self) -> None:
        self.controller.restore_defaults()
        self.init_val = 0.0
        self.expect_val = 0.0
        self.real_val = 0.0
        self.real_rate = 0.0
        self.mode = self.MODE_IDLE
        self._disturbance_params = DisturbanceParams()
        self._disturbance_mode_key = "sine"
        self._disturbance_level_key = "medium"
        self._t = 0.0
        self._disturbance = 0.0

    def apply_params(self, params: LadrcParams) -> None:
        self.controller.apply_params(params)

    def set_disturbance_scale(self, scale: float) -> None:
        self._disturbance_scale = max(0.0, float(scale))

    def set_disturbance_mode(self, mode_key: str) -> None:
        self._disturbance_mode_key = _normalize_disturbance_mode(mode_key)

    def set_disturbance_level(self, level_key: str, scale: float | None = None) -> None:
        self._disturbance_level_key = _normalize_disturbance_level(level_key)
        if scale is not None:
            self.set_disturbance_scale(scale)

    def set_disturbance_params(self, params: DisturbanceParams) -> None:
        self._disturbance_params = DisturbanceParams(
            amplitude_gain=max(0.0, float(params.amplitude_gain)),
            frequency_gain=max(0.0, float(params.frequency_gain)),
            bias=float(params.bias),
        )

    def set_init(self, value: float) -> None:
        self.init_val = float(value)
        self.real_val = self.init_val
        self.real_rate = 0.0
        if self.mode == self.MODE_LOOP:
            self._reset_loop_runtime_states()
        elif self.mode == self.MODE_TD:
            self._reset_td_runtime_states()

    def set_expect(self, value: float) -> None:
        self.expect_val = float(value)

    def _reset_td_runtime_states(self) -> None:
        self.controller.v1 = float(self.real_val)
        self.controller.v2 = 0.0
        self.controller.z1 = float(self.real_val)
        self.controller.z2 = 0.0
        self.controller.z3 = 0.0
        self.controller.u = 0.0

    def _reset_loop_runtime_states(self) -> None:
        self.controller.v1 = float(self.expect_val)
        self.controller.v2 = 0.0
        self.controller.z1 = float(self.real_val)
        self.controller.z2 = 0.0
        self.controller.z3 = 0.0
        self.controller.u = 0.0

    def _runtime_is_finite(self) -> bool:
        values = (
            self.init_val,
            self.expect_val,
            self.real_val,
            self.real_rate,
            self.controller.v1,
            self.controller.v2,
            self.controller.z1,
            self.controller.z2,
            self.controller.z3,
            self.controller.u,
            self.controller.params.r,
            self.controller.params.h,
            self.controller.params.w0,
            self.controller.params.wc,
            self.controller.params.b0,
        )
        return all(math.isfinite(value) for value in values) and self.controller.params.h > 0.0 and self.controller.params.b0 > 0.0

    def _recover_invalid_runtime(self) -> None:
        self.mode = self.MODE_IDLE
        self.real_val = self.init_val
        self.real_rate = 0.0
        self._reset_loop_runtime_states()

    def set_mode(self, mode: int) -> None:
        if mode not in (self.MODE_TD, self.MODE_LOOP, self.MODE_IDLE):
            mode = self.MODE_IDLE
        self.mode = int(mode)
        self.real_rate = 0.0
        if self.mode == self.MODE_LOOP:
            self.real_val = self.init_val
            self._reset_loop_runtime_states()
        elif self.mode == self.MODE_TD:
            self._reset_td_runtime_states()
        else:
            self.controller.u = 0.0

    def reset_runtime(self) -> None:
        self.controller.restore_defaults()
        self.init_val = 0.0
        self.expect_val = 0.0
        self.real_val = 0.0
        self.real_rate = 0.0
        self.mode = self.MODE_IDLE
        self._t = 0.0
        self._disturbance = 0.0

    def run_state(self) -> int:
        return 0 if self.mode == self.MODE_IDLE else 1

    def _sample_disturbance(self, dt: float) -> float:
        self._t += max(dt, 1e-4)
        return _disturbance_wave(
            self._disturbance_mode_key,
            self._disturbance_level_key,
            self.DISTURB_AMP,
            self.DISTURB_FREQ_HZ,
            self._disturbance_scale,
            self._t,
            self._disturbance_params,
        )

    def step(self) -> dict:
        dt = max(self.controller.params.h, 1e-4)
        if self.mode == self.MODE_TD:
            self._disturbance = self._sample_disturbance(dt)
            self.controller.td(self.expect_val)
        elif self.mode == self.MODE_LOOP:
            self._disturbance = self._sample_disturbance(dt)
            acc = (self.controller.u + self._disturbance - self.PLANT_DAMPING * self.real_rate) / self.PLANT_MASS
            self.real_rate += acc * dt
            self.real_val += self.real_rate * dt
            self.controller.loop(self.expect_val, self.real_val)
            if not self._runtime_is_finite():
                self._recover_invalid_runtime()
        else:
            self._disturbance = 0.0
        return self.snapshot()

    def _feedback_output(self) -> float:
        if self.mode == self.MODE_TD:
            return float(self.controller.v1)
        return float(self.real_val)

    def snapshot(self) -> dict:
        return {
            "ref": float(self.expect_val),
            "feedback": self._feedback_output(),
            "u_cmd": float(self.controller.u),
            "sim_mode": float(self.mode),
            "v1": float(self.controller.v1),
            "v2": float(self.controller.v2),
            "z1": float(self.controller.z1),
            "z2": float(self.controller.z2),
            "z3": float(self.controller.z3),
            "disturbance": float(self._disturbance),
            "r": float(self.controller.params.r),
            "h": float(self.controller.params.h),
            "w0": float(self.controller.params.w0),
            "wc": float(self.controller.params.wc),
            "b0": float(self.controller.params.b0),
            "init": float(self.init_val),
            "run_state": float(self.run_state()),
        }


class DepthPlantSimulator:
    def __init__(self, params: PlantParams | None = None) -> None:
        self.params = params or PlantParams()
        self.depth = 0.0
        self.depth_rate = 0.0
        self.last_u = 0.0
        self._t = 0.0
        self._disturbance_params = DisturbanceParams()
        self._disturbance_mode_key = "sine"
        self._disturbance_level_key = "medium"
        self._disturbance_scale = 1.0

    def reset(self, depth: float = 0.0, depth_rate: float = 0.0) -> None:
        self.depth = depth
        self.depth_rate = depth_rate
        self.last_u = 0.0
        self._t = 0.0

    def set_disturbance_scale(self, scale: float) -> None:
        self._disturbance_scale = max(0.0, float(scale))

    def set_disturbance_mode(self, mode_key: str) -> None:
        self._disturbance_mode_key = _normalize_disturbance_mode(mode_key)

    def set_disturbance_level(self, level_key: str, scale: float | None = None) -> None:
        self._disturbance_level_key = _normalize_disturbance_level(level_key)
        if scale is not None:
            self.set_disturbance_scale(scale)

    def set_disturbance_params(self, params: DisturbanceParams) -> None:
        self._disturbance_params = DisturbanceParams(
            amplitude_gain=max(0.0, float(params.amplitude_gain)),
            frequency_gain=max(0.0, float(params.frequency_gain)),
            bias=float(params.bias),
        )

    def step(self, dt: float, u: float) -> SimFeedback:
        dt = max(1e-4, dt)
        self._t += dt
        self.last_u = u

        disturb = _disturbance_wave(
            self._disturbance_mode_key,
            self._disturbance_level_key,
            self.params.disturb_amp,
            self.params.disturb_freq_hz,
            self._disturbance_scale,
            self._t,
            self._disturbance_params,
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

