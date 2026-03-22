from dataclasses import dataclass


@dataclass
class AppConfig:
    app_name: str = "控制算法模拟器-by嵌入式新起点"
    app_version: str = "v1.0"
    app_author: str = "嵌入式新起点"
    app_tagline: str = "控制算法联调、波形分析与三维仿真一体化工具"
    ui_refresh_hz: int = 30
    sim_hz: int = 100
    serial_tx_hz: int = 25
    serial_timeout_s: float = 0.05
    communication_timeout_ms: int = 300
    plot_window_sec: float = 20.0
    max_plot_points: int = 3000


DEFAULT_CONFIG = AppConfig()
