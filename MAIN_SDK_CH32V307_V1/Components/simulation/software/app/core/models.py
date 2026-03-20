from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Telemetry:
    timestamp_ms: int = 0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    u_cmd: float = 0.0
    ref: float = 0.0
    feedback: float = 0.0
    algo_id: int = 0
    run_state: int = 0
    extra: Dict[str, float] = field(default_factory=dict)


@dataclass
class SimFeedback:
    timestamp_ms: int
    depth: float
    depth_rate: float
    disturbance: float


@dataclass
class CommStats:
    rx_frames: int = 0
    tx_frames: int = 0
    parse_errors: int = 0
    dropped: int = 0
    last_rx_ms: int = 0
    last_latency_ms: int = 0

