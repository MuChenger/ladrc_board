from dataclasses import dataclass


@dataclass
class AppConfig:
    app_name: str = "Control Simulation Host"
    ui_refresh_hz: int = 30
    sim_hz: int = 100
    serial_tx_hz: int = 25
    serial_timeout_s: float = 0.05
    communication_timeout_ms: int = 300
    plot_window_sec: float = 20.0
    max_plot_points: int = 3000


DEFAULT_CONFIG = AppConfig()

