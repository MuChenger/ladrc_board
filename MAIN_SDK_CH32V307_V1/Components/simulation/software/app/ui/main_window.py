import json
import math
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from ..config import DEFAULT_CONFIG
from ..core.models import SimFeedback, Telemetry
from ..core.protocol import telemetry_to_record_dict
from ..core.recorder import CsvRecorder
from ..core.serial_worker import SerialWorker
from ..core.simulator import DepthPlantSimulator, PlantParams
from .panels.command_panel import CommandPanel
from .panels.log_panel import LogPanel
from .panels.model_3d_panel import Model3DPanel
from .panels.plot_panel import PlotPanel
from .panels.preset_command_panel import PresetCommandPanel
from .panels.serial_panel import SerialPanel
from .panels.status_panel import StatusPanel


ALGO_NAME = {0: "PID", 1: "LADRC", 2: "开环"}
MODEL_NAME = {"rov": "水下机器人", "aircraft": "飞行器", "generic": "通用载体"}
SOFTWARE_ROOT = Path(__file__).resolve().parents[2]
APP_ICON_PATH = SOFTWARE_ROOT / "assets" / "icons" / "app_icon.svg"
DISTURBANCE_LEVEL_TEXT = {
    "off": "关闭",
    "low": "低",
    "medium": "中",
    "high": "高",
    "extreme": "极高",
}
DEFAULT_THEME_KEY = "ocean"
THEME_ORDER = ["ocean", "light", "dark"]


def _default_user_settings_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "EmbeddedNewStart" / "ControlAlgorithmSimulator"
        return Path.home() / "AppData" / "Roaming" / "EmbeddedNewStart" / "ControlAlgorithmSimulator"

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "embedded-newstart" / "control-algorithm-simulator"
    return Path.home() / ".config" / "embedded-newstart" / "control-algorithm-simulator"


USER_SETTINGS_DIR = _default_user_settings_dir()
USER_SETTINGS_PATH = USER_SETTINGS_DIR / "user_settings.json"
LEGACY_USER_SETTINGS_PATH = SOFTWARE_ROOT / "user_settings.json"
THEME_PRESETS = {
    "light": {
        "label": "浅色专业",
        "window_bg": "#f3f5f7",
        "surface": "#ffffff",
        "surface_alt": "#f7f9fb",
        "toolbar_bg": "#eceff3",
        "menu_bg": "#ffffff",
        "menu_hover": "#dfe9f4",
        "menubar_hover": "#dfe6ee",
        "border": "#ccd5de",
        "border_strong": "#bec8d2",
        "separator": "#c8d0d8",
        "text": "#1d2e3f",
        "title_text": "#22405d",
        "muted": "#667b90",
        "value_text": "#12314c",
        "dock_title_bg": "#e7ebf0",
        "dock_title_text": "#26415c",
        "accent": "#2d70b3",
        "button_bg": "#ffffff",
        "button_hover": "#f0f4f8",
        "button_pressed": "#e3ebf3",
        "disabled_text": "#8a98a7",
        "disabled_bg": "#f5f7f9",
        "input_bg": "#ffffff",
        "selection_bg": "#2d70b3",
        "group_title": "#2a3d53",
        "console_bg": "#111827",
        "console_text": "#d7e2f0",
        "placeholder_bg": "#ffffff",
        "placeholder_border": "#bcc8d5",
        "statusbar_bg": "#eceff3",
        "scroll_bg": "#f3f5f7",
        "summary_text": "#586b7d",
        "tab_bg": "#e9eef4",
        "tab_selected": "#ffffff",
        "tab_hover": "#f4f7fa",
        "tab_text": "#43586d",
        "plot_background": "#ffffff",
        "plot_axis": "#61758a",
        "plot_text": "#294055",
        "plot_grid_alpha": 0.16,
        "plot_cursor": (80, 98, 120, 150),
        "plot_measure_a": "#c58a00",
        "plot_measure_b": "#157bc1",
        "plot_annotation_bg": "rgba(255,255,255,235)",
        "plot_annotation_text": "#213140",
        "plot_annotation_border": "rgba(84,104,124,90)",
        "model_metric_bg": "rgba(248,251,255,0.96)",
        "model_metric_border": "#d5e1ec",
        "model_metric_text": "#1b3953",
        "model_view_border": "rgba(130,156,182,96)",
        "model_hud_bg": "rgba(18,30,44,178)",
        "model_hud_border": "rgba(255,255,255,74)",
        "model_hud_title": "rgba(245,248,252,232)",
        "model_hud_text": "rgba(226,234,242,215)",
        "model_backgrounds": {
            "aircraft": "#b9dcff",
            "trajectory": "#27425f",
            "underwater": "#4a6a86",
            "attitude": "#314a66",
        },
    },
    "dark": {
        "label": "深色夜航",
        "window_bg": "#11161d",
        "surface": "#18202a",
        "surface_alt": "#1d2630",
        "toolbar_bg": "#131a22",
        "menu_bg": "#1a232e",
        "menu_hover": "#243244",
        "menubar_hover": "#223041",
        "border": "#2c3947",
        "border_strong": "#3a4a5b",
        "separator": "#30404f",
        "text": "#e5edf7",
        "title_text": "#f4f8fb",
        "muted": "#9aa9bb",
        "value_text": "#f2f7fb",
        "dock_title_bg": "#17202a",
        "dock_title_text": "#e8f0f8",
        "accent": "#4ea1ff",
        "button_bg": "#1d2732",
        "button_hover": "#243141",
        "button_pressed": "#2b394b",
        "disabled_text": "#6e7f90",
        "disabled_bg": "#151c24",
        "input_bg": "#121922",
        "selection_bg": "#3b84db",
        "group_title": "#d6e4f2",
        "console_bg": "#0a0f15",
        "console_text": "#dbe9f8",
        "placeholder_bg": "#17202a",
        "placeholder_border": "#405164",
        "statusbar_bg": "#121922",
        "scroll_bg": "#11161d",
        "summary_text": "#9db2c7",
        "tab_bg": "#1b2430",
        "tab_selected": "#243244",
        "tab_hover": "#2b394c",
        "tab_text": "#c0d1e2",
        "plot_background": "#0c1218",
        "plot_axis": "#9cb0c4",
        "plot_text": "#d9e4ee",
        "plot_grid_alpha": 0.22,
        "plot_cursor": (190, 210, 230, 165),
        "plot_measure_a": "#ffc44d",
        "plot_measure_b": "#5bc0ff",
        "plot_annotation_bg": "rgba(17,24,39,236)",
        "plot_annotation_text": "#ecf3fb",
        "plot_annotation_border": "rgba(157,178,199,92)",
        "model_metric_bg": "rgba(28,39,52,0.96)",
        "model_metric_border": "#35506a",
        "model_metric_text": "#e4eef7",
        "model_view_border": "rgba(168,190,214,72)",
        "model_hud_bg": "rgba(8,14,20,196)",
        "model_hud_border": "rgba(171,193,216,72)",
        "model_hud_title": "rgba(244,248,252,232)",
        "model_hud_text": "rgba(215,228,241,220)",
        "model_backgrounds": {
            "aircraft": "#6d8fb0",
            "trajectory": "#162331",
            "underwater": "#214462",
            "attitude": "#1c2f42",
        },
    },
    "ocean": {
        "label": "海洋蓝调",
        "window_bg": "#e8f1f4",
        "surface": "#f8fbfc",
        "surface_alt": "#eef6f8",
        "toolbar_bg": "#deedf3",
        "menu_bg": "#f8fcfd",
        "menu_hover": "#d8ecf3",
        "menubar_hover": "#d5e7ee",
        "border": "#bfd0da",
        "border_strong": "#aabecb",
        "separator": "#b5cad6",
        "text": "#153247",
        "title_text": "#18405e",
        "muted": "#5e798d",
        "value_text": "#10344f",
        "dock_title_bg": "#dcebf2",
        "dock_title_text": "#1e4766",
        "accent": "#1f90a8",
        "button_bg": "#ffffff",
        "button_hover": "#edf8fb",
        "button_pressed": "#d9edf3",
        "disabled_text": "#8ca2b0",
        "disabled_bg": "#eef4f6",
        "input_bg": "#ffffff",
        "selection_bg": "#1f90a8",
        "group_title": "#24506a",
        "console_bg": "#0f2431",
        "console_text": "#dbf3ff",
        "placeholder_bg": "#fafdff",
        "placeholder_border": "#aac9d8",
        "statusbar_bg": "#deedf3",
        "scroll_bg": "#e8f1f4",
        "summary_text": "#567589",
        "tab_bg": "#e0ecf1",
        "tab_selected": "#f8fbfc",
        "tab_hover": "#edf7fa",
        "tab_text": "#406176",
        "plot_background": "#f9fdff",
        "plot_axis": "#547187",
        "plot_text": "#234157",
        "plot_grid_alpha": 0.18,
        "plot_cursor": (67, 108, 137, 150),
        "plot_measure_a": "#c28b00",
        "plot_measure_b": "#0084a8",
        "plot_annotation_bg": "rgba(248,252,255,238)",
        "plot_annotation_text": "#1f3b4f",
        "plot_annotation_border": "rgba(72,118,146,88)",
        "model_metric_bg": "rgba(247,252,255,0.96)",
        "model_metric_border": "#cde0ea",
        "model_metric_text": "#19415a",
        "model_view_border": "rgba(119,174,196,88)",
        "model_hud_bg": "rgba(13,32,44,176)",
        "model_hud_border": "rgba(210,235,246,76)",
        "model_hud_title": "rgba(244,251,255,232)",
        "model_hud_text": "rgba(223,239,246,218)",
        "model_backgrounds": {
            "aircraft": "#c5e7ff",
            "trajectory": "#1f415b",
            "underwater": "#44759a",
            "attitude": "#2c5878",
        },
    },
}


class WaveformDetachedWindow(QtWidgets.QWidget):
    close_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.Window)
        self._display_mode = "floating"
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        self.setWindowTitle("波形窗口")
        self.resize(1180, 760)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def apply_display_mode(self, mode: str):
        self._display_mode = mode
        was_visible = self.isVisible()
        normal_geometry = self.geometry()
        if mode == "fullscreen":
            flags = (
                QtCore.Qt.Window
                | QtCore.Qt.CustomizeWindowHint
                | QtCore.Qt.WindowTitleHint
                | QtCore.Qt.WindowMinimizeButtonHint
                | QtCore.Qt.WindowCloseButtonHint
            )
        else:
            flags = (
                QtCore.Qt.Window
                | QtCore.Qt.CustomizeWindowHint
                | QtCore.Qt.WindowTitleHint
                | QtCore.Qt.WindowMinimizeButtonHint
                | QtCore.Qt.WindowMaximizeButtonHint
                | QtCore.Qt.WindowCloseButtonHint
            )
        self.setWindowFlags(flags)
        if was_visible:
            self.show()
            if mode == "fullscreen":
                self.showMaximized()
            else:
                self.showNormal()
                if normal_geometry.isValid():
                    self.setGeometry(normal_geometry)

    def closeEvent(self, event):
        self.hide()
        self.close_requested.emit()
        event.ignore()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape and self._display_mode == "fullscreen":
            self.hide()
            self.close_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class StartupOrbWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(110, 110)
        self._angle = 0.0
        self._phase = 0.0
        self._icon = QtGui.QIcon(str(APP_ICON_PATH)) if APP_ICON_PATH.exists() else QtGui.QIcon()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._advance_animation)
        self._timer.start()

    def _advance_animation(self):
        self._angle = (self._angle + 4.2) % 360.0
        self._phase = (self._phase + 0.09) % (math.pi * 2.0)
        self.update()

    def paintEvent(self, event):  # pragma: no cover - UI paint
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        rect = self.rect().adjusted(6, 6, -6, -6)
        center = rect.center()

        glow_radius = 42 + math.sin(self._phase) * 4.0
        glow_color = QtGui.QColor(47, 199, 164, 42)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(glow_color)
        painter.drawEllipse(center, glow_radius, glow_radius)

        outer_rect = QtCore.QRectF(center.x() - 40, center.y() - 40, 80, 80)
        ring_pen = QtGui.QPen(QtGui.QColor(31, 144, 168, 110), 4.0)
        painter.setPen(ring_pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawEllipse(outer_rect)

        arc_pen = QtGui.QPen(QtGui.QColor(34, 95, 167, 210), 5.5)
        arc_pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(arc_pen)
        painter.drawArc(outer_rect, int(-self._angle * 16), int(-110 * 16))

        inner_rect = QtCore.QRectF(center.x() - 29, center.y() - 29, 58, 58)
        gradient = QtGui.QRadialGradient(inner_rect.center(), 34)
        gradient.setColorAt(0.0, QtGui.QColor("#f8fdff"))
        gradient.setColorAt(0.55, QtGui.QColor("#dceffe"))
        gradient.setColorAt(1.0, QtGui.QColor("#7db8db"))
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 140), 1.4))
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawEllipse(inner_rect)

        if not self._icon.isNull():
            icon_rect = inner_rect.adjusted(12, 12, -12, -12).toRect()
            self._icon.paint(painter, icon_rect)

        orbit_radius = 40
        for index, color in enumerate((QtGui.QColor("#2fc7a4"), QtGui.QColor("#1f90a8"), QtGui.QColor("#9fe3f1"))):
            angle = math.radians(self._angle + index * 120)
            point = QtCore.QPointF(
                center.x() + math.cos(angle) * orbit_radius,
                center.y() + math.sin(angle) * orbit_radius,
            )
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(point, 4.2 - index * 0.6, 4.2 - index * 0.6)


class StartupSplash(QtWidgets.QWidget):
    def __init__(self, config, parent=None):
        super().__init__(
            parent,
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.SplashScreen | QtCore.Qt.WindowStaysOnTopHint,
        )
        self._config = config
        self._status_base_text = "正在初始化启动环境"
        self._dot_count = 0
        self._intro_animation = None
        self._finish_group = None
        self._window_fade_animation = None
        self._progress_animation = None
        self._supports_window_opacity = QtWidgets.QApplication.instance().platformName() not in {"offscreen", "minimal"}
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.resize(560, 320)
        self._build()

        self._dot_timer = QtCore.QTimer(self)
        self._dot_timer.setInterval(260)
        self._dot_timer.timeout.connect(self._advance_loading_dots)
        self._dot_timer.start()

    def _build(self):
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(0)

        self.card = QtWidgets.QFrame()
        self.card.setObjectName("startupCard")
        self.card.setStyleSheet(
            """
            QFrame#startupCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(250, 253, 255, 250),
                    stop:0.42 rgba(233, 246, 251, 246),
                    stop:1 rgba(204, 230, 242, 242));
                border: 1px solid rgba(78, 141, 172, 102);
                border-radius: 24px;
            }
            QFrame#startupTopStripe {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(47, 199, 164, 210),
                    stop:0.55 rgba(31, 144, 168, 226),
                    stop:1 rgba(34, 95, 167, 214));
                border-radius: 6px;
            }
            QLabel#startupTitle {
                color: #18405e;
                font-size: 21px;
                font-weight: 700;
            }
            QLabel#startupVersion {
                color: #2f6b86;
                background: rgba(31, 144, 168, 28);
                border: 1px solid rgba(31, 144, 168, 68);
                border-radius: 10px;
                padding: 4px 10px;
                font-weight: 600;
            }
            QLabel#startupTagline {
                color: #527184;
                font-size: 12px;
            }
            QLabel#startupStatus {
                color: #16384f;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#startupHint {
                color: #5c7688;
                font-size: 11px;
            }
            QLabel#startupFootnote {
                color: #6f8897;
                font-size: 10px;
            }
            QProgressBar#startupProgress {
                border: 1px solid rgba(101, 149, 177, 65);
                border-radius: 8px;
                background: rgba(255, 255, 255, 185);
                height: 12px;
            }
            QProgressBar#startupProgress::chunk {
                border-radius: 7px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2fc7a4, stop:1 #1f90a8);
                margin: 1px;
            }
            """
        )
        root_layout.addWidget(self.card)

        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 22, 24, 20)
        card_layout.setSpacing(14)

        top_stripe = QtWidgets.QFrame()
        top_stripe.setObjectName("startupTopStripe")
        top_stripe.setFixedHeight(8)
        card_layout.addWidget(top_stripe)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(16)

        self.orb_widget = StartupOrbWidget()
        header_layout.addWidget(self.orb_widget, 0, QtCore.Qt.AlignTop)

        title_layout = QtWidgets.QVBoxLayout()
        title_layout.setSpacing(6)
        self.title_label = QtWidgets.QLabel(self._config.app_name)
        self.title_label.setObjectName("startupTitle")
        self.title_label.setWordWrap(True)
        self.version_label = QtWidgets.QLabel(self._config.app_version)
        self.version_label.setObjectName("startupVersion")
        self.version_label.setAlignment(QtCore.Qt.AlignCenter)
        self.version_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.tagline_label = QtWidgets.QLabel(self._config.app_tagline)
        self.tagline_label.setObjectName("startupTagline")
        self.tagline_label.setWordWrap(True)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.version_label, 0, QtCore.Qt.AlignLeft)
        title_layout.addWidget(self.tagline_label)
        title_layout.addStretch(1)
        header_layout.addLayout(title_layout, 1)
        card_layout.addLayout(header_layout)

        self.status_label = QtWidgets.QLabel()
        self.status_label.setObjectName("startupStatus")
        self.status_label.setWordWrap(True)
        card_layout.addWidget(self.status_label)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setObjectName("startupProgress")
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(12)
        card_layout.addWidget(self.progress)

        self.hint_label = QtWidgets.QLabel("正在准备串口联调、波形工作台与三维仿真环境")
        self.hint_label.setObjectName("startupHint")
        self.hint_label.setWordWrap(True)
        card_layout.addWidget(self.hint_label)

        self.footnote_label = QtWidgets.QLabel("海洋蓝调工作台正在启动")
        self.footnote_label.setObjectName("startupFootnote")
        self.footnote_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        card_layout.addWidget(self.footnote_label)

        self._refresh_status_text()

    def _refresh_status_text(self):
        dots = "." * self._dot_count
        self.status_label.setText(f"{self._status_base_text}{dots}")

    def _advance_loading_dots(self):
        self._dot_count = (self._dot_count + 1) % 4
        self._refresh_status_text()

    def set_stage_text(self, text: str):
        self._status_base_text = text.strip() or self._status_base_text
        self._refresh_status_text()

    def set_stage_info(self, text: str, hint: str | None = None, progress: int | None = None):
        self._status_base_text = text.strip() or self._status_base_text
        if hint is not None:
            self.hint_label.setText(hint)
        if progress is not None:
            progress = max(0, min(int(progress), 100))
            if self.progress.value() != progress:
                self._progress_animation = QtCore.QPropertyAnimation(self.progress, b"value", self)
                self._progress_animation.setDuration(260)
                self._progress_animation.setStartValue(self.progress.value())
                self._progress_animation.setEndValue(progress)
                self._progress_animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
                self._progress_animation.start()
        self._refresh_status_text()

    def show_centered(self):
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.availableGeometry()
            self.move(geometry.center() - self.rect().center())
        if self._supports_window_opacity:
            self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()
        if self._supports_window_opacity:
            self._intro_animation = QtCore.QPropertyAnimation(self, b"windowOpacity", self)
            self._intro_animation.setDuration(320)
            self._intro_animation.setStartValue(0.0)
            self._intro_animation.setEndValue(1.0)
            self._intro_animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
            self._intro_animation.start()

    def finish_with(self, window: QtWidgets.QWidget):
        self._dot_timer.stop()
        self.set_stage_info("准备完成，正在打开工作台", "正在将海洋蓝调工作台切换到主界面", 100)

        if self._supports_window_opacity:
            window.setWindowOpacity(0.0)
        window.show()
        window.raise_()
        window.activateWindow()

        if not self._supports_window_opacity:
            self.close()
            return

        self._window_fade_animation = QtCore.QPropertyAnimation(window, b"windowOpacity", window)
        self._window_fade_animation.setDuration(320)
        self._window_fade_animation.setStartValue(0.0)
        self._window_fade_animation.setEndValue(1.0)
        self._window_fade_animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        splash_fade = QtCore.QPropertyAnimation(self, b"windowOpacity", self)
        splash_fade.setDuration(260)
        splash_fade.setStartValue(self.windowOpacity())
        splash_fade.setEndValue(0.0)
        splash_fade.setEasingCurve(QtCore.QEasingCurve.InCubic)

        self._finish_group = QtCore.QParallelAnimationGroup(self)
        self._finish_group.addAnimation(self._window_fade_animation)
        self._finish_group.addAnimation(splash_fade)
        self._finish_group.finished.connect(self.close)
        self._finish_group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)


class WelcomeDialog(QtWidgets.QDialog):
    show_on_startup_changed = QtCore.pyqtSignal(bool)
    open_device_requested = QtCore.pyqtSignal()
    open_control_requested = QtCore.pyqtSignal()
    open_wave_requested = QtCore.pyqtSignal()
    open_model_requested = QtCore.pyqtSignal()

    def __init__(self, config, icon: QtGui.QIcon, parent=None):
        super().__init__(parent, QtCore.Qt.Dialog | QtCore.Qt.WindowCloseButtonHint)
        self._config = config
        self._icon = icon
        self.setModal(False)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        self.setWindowTitle(f"欢迎使用 {self._config.app_name}")
        self.resize(640, 420)
        if not self._icon.isNull():
            self.setWindowIcon(self._icon)
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        hero_card = QtWidgets.QFrame()
        hero_card.setObjectName("recordCard")
        hero_layout = QtWidgets.QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(16, 16, 16, 16)
        hero_layout.setSpacing(16)

        icon_label = QtWidgets.QLabel()
        icon_label.setFixedSize(86, 86)
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        if not self._icon.isNull():
            icon_label.setPixmap(self._icon.pixmap(86, 86))
        hero_layout.addWidget(icon_label, 0, QtCore.Qt.AlignTop)

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(6)
        title_label = QtWidgets.QLabel(self._config.app_name)
        title_label.setObjectName("sectionTitle")
        title_label.setWordWrap(True)
        version_label = QtWidgets.QLabel(self._config.app_version)
        version_label.setObjectName("statusHint")
        tagline_label = QtWidgets.QLabel(self._config.app_tagline)
        tagline_label.setWordWrap(True)
        tagline_label.setObjectName("statusHint")
        text_layout.addWidget(title_label)
        text_layout.addWidget(version_label)
        text_layout.addWidget(tagline_label)
        text_layout.addStretch(1)
        hero_layout.addLayout(text_layout, 1)
        layout.addWidget(hero_card)

        self.first_launch_label = QtWidgets.QLabel("")
        self.first_launch_label.setObjectName("statusHint")
        self.first_launch_label.setWordWrap(True)
        layout.addWidget(self.first_launch_label)

        intro_label = QtWidgets.QLabel(
            "欢迎来到控制算法模拟器工作台。你可以在这里完成控制算法联调、波形分析、数据录制，以及三维姿态与场景观察。"
        )
        intro_label.setWordWrap(True)
        layout.addWidget(intro_label)

        content_row = QtWidgets.QHBoxLayout()
        content_row.setSpacing(12)

        quick_start_card = QtWidgets.QFrame()
        quick_start_card.setObjectName("recordCard")
        quick_start_layout = QtWidgets.QVBoxLayout(quick_start_card)
        quick_start_layout.setContentsMargins(14, 14, 14, 14)
        quick_start_layout.setSpacing(8)
        quick_start_title = QtWidgets.QLabel("快速开始")
        quick_start_title.setObjectName("sectionTitle")
        quick_start_layout.addWidget(quick_start_title)
        quick_start_steps = QtWidgets.QLabel(
            "1. 在左侧“设备”页选择串口并连接。\n"
            "2. 在“控制”页设置参考值、算法和扰动等级。\n"
            "3. 在中间波形区观察响应，在右侧查看 3D 场景。\n"
            "4. 需要时可录制 CSV 或导入外部模型。"
        )
        quick_start_steps.setWordWrap(True)
        quick_start_layout.addWidget(quick_start_steps)
        content_row.addWidget(quick_start_card, 1)

        highlights_card = QtWidgets.QFrame()
        highlights_card.setObjectName("recordCard")
        highlights_layout = QtWidgets.QVBoxLayout(highlights_card)
        highlights_layout.setContentsMargins(14, 14, 14, 14)
        highlights_layout.setSpacing(8)
        highlights_title = QtWidgets.QLabel("本次工作台亮点")
        highlights_title.setObjectName("sectionTitle")
        highlights_layout.addWidget(highlights_title)
        highlights_text = QtWidgets.QLabel(
            "• 海洋蓝调主题与品牌化启动体验\n"
            "• Eclipse 风格工作台布局\n"
            "• 波形测量、标记、全屏与小窗\n"
            "• 3D 模型、场景模式与主题联动"
        )
        highlights_text.setWordWrap(True)
        highlights_layout.addWidget(highlights_text)
        content_row.addWidget(highlights_card, 1)

        layout.addLayout(content_row)

        summary_card = QtWidgets.QFrame()
        summary_card.setObjectName("recordCard")
        summary_layout = QtWidgets.QFormLayout(summary_card)
        summary_layout.setContentsMargins(14, 14, 14, 14)
        summary_layout.setHorizontalSpacing(18)
        summary_layout.setVerticalSpacing(8)
        summary_layout.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.theme_value_label = QtWidgets.QLabel("--")
        self.model_value_label = QtWidgets.QLabel("--")
        self.scene_value_label = QtWidgets.QLabel("--")
        self.startup_value_label = QtWidgets.QLabel("--")
        for value_label in (
            self.theme_value_label,
            self.model_value_label,
            self.scene_value_label,
            self.startup_value_label,
        ):
            value_label.setProperty("statusValue", True)
        summary_layout.addRow("当前主题", self.theme_value_label)
        summary_layout.addRow("当前模型", self.model_value_label)
        summary_layout.addRow("当前场景", self.scene_value_label)
        summary_layout.addRow("欢迎页设置", self.startup_value_label)
        layout.addWidget(summary_card)

        quick_actions_card = QtWidgets.QFrame()
        quick_actions_card.setObjectName("recordCard")
        quick_actions_layout = QtWidgets.QVBoxLayout(quick_actions_card)
        quick_actions_layout.setContentsMargins(14, 14, 14, 14)
        quick_actions_layout.setSpacing(8)
        quick_title = QtWidgets.QLabel("快速入口")
        quick_title.setObjectName("sectionTitle")
        quick_actions_layout.addWidget(quick_title)
        quick_grid = QtWidgets.QGridLayout()
        quick_grid.setHorizontalSpacing(8)
        quick_grid.setVerticalSpacing(8)
        self.device_btn = QtWidgets.QPushButton("设备连接")
        self.control_btn = QtWidgets.QPushButton("控制参数")
        self.wave_btn = QtWidgets.QPushButton("波形工作台")
        self.model_btn = QtWidgets.QPushButton("3D 视图")
        quick_grid.addWidget(self.device_btn, 0, 0)
        quick_grid.addWidget(self.control_btn, 0, 1)
        quick_grid.addWidget(self.wave_btn, 1, 0)
        quick_grid.addWidget(self.model_btn, 1, 1)
        quick_actions_layout.addLayout(quick_grid)
        layout.addWidget(quick_actions_card)

        self.show_on_startup_cb = QtWidgets.QCheckBox("启动时显示欢迎页")
        self.show_on_startup_cb.setChecked(True)
        self.show_on_startup_cb.toggled.connect(self.show_on_startup_changed.emit)
        layout.addWidget(self.show_on_startup_cb)

        buttons = QtWidgets.QDialogButtonBox()
        self.start_btn = buttons.addButton("开始使用", QtWidgets.QDialogButtonBox.AcceptRole)
        self.device_btn.clicked.connect(self.open_device_requested.emit)
        self.control_btn.clicked.connect(self.open_control_requested.emit)
        self.wave_btn.clicked.connect(self.open_wave_requested.emit)
        self.model_btn.clicked.connect(self.open_model_requested.emit)
        self.start_btn.clicked.connect(self.accept)
        layout.addWidget(buttons)

    def set_show_on_startup(self, enabled: bool):
        blocker = QtCore.QSignalBlocker(self.show_on_startup_cb)
        self.show_on_startup_cb.setChecked(bool(enabled))
        del blocker

    def set_context(self, theme_text: str, model_text: str, scene_text: str, show_on_startup: bool, first_launch: bool):
        self.theme_value_label.setText(theme_text or "--")
        self.model_value_label.setText(model_text or "--")
        self.scene_value_label.setText(scene_text or "--")
        self.startup_value_label.setText("启动时显示" if show_on_startup else "仅手动打开")
        if first_launch:
            self.first_launch_label.setText("首次启动已默认为你打开欢迎页，后续可通过下方选项决定是否继续显示。")
        else:
            self.first_launch_label.setText("欢迎页可通过“帮助 -> 欢迎页”随时再次打开。")


class MainWindow(QtWidgets.QMainWindow):
    send_line_signal = QtCore.pyqtSignal(str)
    send_feedback_signal = QtCore.pyqtSignal(object)
    open_serial_signal = QtCore.pyqtSignal(str, int)
    close_serial_signal = QtCore.pyqtSignal()
    set_binary_signal = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.cfg = replace(DEFAULT_CONFIG)
        self.setWindowTitle(self.cfg.app_name)
        self._set_app_icon()
        self.resize(1600, 940)

        self._default_window_state = None
        self._default_window_geometry = None
        self._latest_telemetry = Telemetry()
        self._feedback_by_model = self._build_feedback_store()
        self._simulators = self._build_simulators()
        self._latest_feedback = self._feedback_by_model["rov"]
        self._start_monotonic = time.monotonic()
        self._last_serial_tx = 0.0
        self._last_rx_ms = 0
        self._last_stats = {"rx_frames": 0, "tx_frames": 0, "parse_errors": 0, "latency_ms": 0}
        self._disturbance_level_key = "medium"
        self._disturbance_scale = 1.0
        self._simulation_running = False
        self._simulate_device_upload = False
        self._simulated_upload_integral = 0.0
        self._simulated_upload_yaw = 0.0
        self._simulated_upload_rx_frames = 0
        self._waveform_window = None
        self._waveform_window_mode = None
        self._console_dock_restoring = False
        self._theme_key = DEFAULT_THEME_KEY
        self._theme_user_selected = False
        self._left_sidebar_target_width = 0
        self._show_welcome_on_startup = True
        self._welcome_seen = False
        self._settings_save_error = ""
        self._welcome_dialog = None
        self._legacy_binary_feedback_warned = False

        self.recorder = CsvRecorder()

        self._build_ui()
        self._apply_theme(self._theme_key, persist=False, show_message=False)
        self._setup_worker()
        self._setup_timers()
        self._refresh_ports()
        self._on_model_context_changed()
        self._capture_default_layout()
        self._load_persistent_settings()
        self._ensure_left_sidebar_visibility()

    def closeEvent(self, event):
        if self._waveform_window_mode is not None:
            self._restore_waveform_embedded()
        self._save_persistent_settings()
        self.close_serial_signal.emit()
        self.worker_thread.quit()
        self.worker_thread.wait(1000)
        self.recorder.stop()
        super().closeEvent(event)

    def _build_feedback_store(self):
        empty = SimFeedback(timestamp_ms=0, depth=0.0, depth_rate=0.0, disturbance=0.0)
        return {
            "rov": empty,
            "aircraft": SimFeedback(**empty.__dict__),
            "generic": SimFeedback(**empty.__dict__),
        }

    def _build_simulators(self):
        return {
            "rov": DepthPlantSimulator(
                PlantParams(
                    mass=8.0,
                    damping=2.8,
                    buoyancy_bias=-0.3,
                    noise_std=0.005,
                    disturb_amp=0.2,
                    disturb_freq_hz=0.15,
                )
            ),
            "aircraft": DepthPlantSimulator(
                PlantParams(
                    mass=6.4,
                    damping=3.4,
                    buoyancy_bias=0.34,
                    noise_std=0.003,
                    disturb_amp=0.08,
                    disturb_freq_hz=0.11,
                )
            ),
            "generic": DepthPlantSimulator(
                PlantParams(
                    mass=7.2,
                    damping=2.2,
                    buoyancy_bias=0.0,
                    noise_std=0.004,
                    disturb_amp=0.12,
                    disturb_freq_hz=0.08,
                )
            ),
        }

    def _build_ui(self):
        self.serial_panel = SerialPanel()
        self.command_panel = CommandPanel()
        self.preset_command_panel = PresetCommandPanel()
        self.log_panel = LogPanel()
        self.status_panel = StatusPanel()
        self.plot_panel = PlotPanel(window_sec=self.cfg.plot_window_sec)
        self.model_panel = Model3DPanel()
        self.channel_widget = self.plot_panel.take_channel_widget()

        self.central_host = QtWidgets.QWidget()
        self.central_layout = QtWidgets.QVBoxLayout(self.central_host)
        self.central_layout.setContentsMargins(8, 8, 8, 8)
        self.central_layout.setSpacing(0)
        self.plot_placeholder = self._create_plot_placeholder()
        self.central_layout.addWidget(self.plot_panel, 1)
        self.central_layout.addWidget(self.plot_placeholder, 1)
        self.plot_placeholder.hide()
        self.setCentralWidget(self.central_host)

        self.setDockOptions(
            QtWidgets.QMainWindow.AnimatedDocks
            | QtWidgets.QMainWindow.AllowTabbedDocks
            | QtWidgets.QMainWindow.AllowNestedDocks
        )
        self.setTabPosition(
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea | QtCore.Qt.BottomDockWidgetArea,
            QtWidgets.QTabWidget.North,
        )

        self._build_top_navigation()
        self._build_workbench_docks()

        self.serial_panel.refresh_requested.connect(self._refresh_ports)
        self.serial_panel.connect_requested.connect(self.open_serial_signal.emit)
        self.serial_panel.disconnect_requested.connect(self.close_serial_signal.emit)
        self.serial_panel.binary_tx_changed.connect(self.set_binary_signal.emit)

        self.command_panel.send_command.connect(self._send_command)
        self.command_panel.algo_selected.connect(self._on_algorithm_selected)
        self.command_panel.ref_changed.connect(self._on_reference_changed)
        self.command_panel.disturbance_level_changed.connect(self._on_disturbance_level_changed)
        self.command_panel.sim_period_changed.connect(self._on_sim_period_changed)
        self.command_panel.simulated_upload_changed.connect(self._on_simulated_upload_changed)
        self.preset_command_panel.send_command.connect(self._send_preset_command)
        self.record_btn.clicked.connect(self._toggle_record)
        self.model_panel.model_combo.currentIndexChanged.connect(self._on_model_context_changed)

        self._on_disturbance_level_changed(
            self.command_panel.current_disturbance_key(),
            self.command_panel.current_disturbance_scale(),
        )
        self._sync_local_control_cache()
        self._on_simulated_upload_changed(self.command_panel.is_simulated_upload_enabled())
        self._sync_navigation_state()
        self._sync_toolbar_state()

    def _build_workbench_docks(self):
        connection_view = self._make_connection_view()
        control_view = self._make_control_view()
        channel_view = self._wrap_scroll_area(self.channel_widget)
        self._left_sidebar_target_width = self._calculate_sidebar_target_width(
            connection_view,
            control_view,
            channel_view,
        )

        self.connection_dock = self._create_dock("设备", connection_view, "dock_connection")
        self.control_dock = self._create_dock("控制", control_view, "dock_control")
        self.channel_dock = self._create_dock("通道", channel_view, "dock_channels")
        self.model_dock = self._create_dock("3D 视图", self.model_panel, "dock_model")
        self.status_dock = self._create_dock("运行状态", self.status_panel, "dock_status")
        self.log_dock = self._create_dock("控制台", self.log_panel, "dock_console")

        for dock in (self.connection_dock, self.control_dock, self.channel_dock):
            dock.setMinimumWidth(self._left_sidebar_target_width)

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.connection_dock)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.control_dock)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.channel_dock)
        self.tabifyDockWidget(self.connection_dock, self.control_dock)
        self.tabifyDockWidget(self.control_dock, self.channel_dock)
        self.connection_dock.raise_()

        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.model_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.status_dock)
        self.tabifyDockWidget(self.model_dock, self.status_dock)
        self.model_dock.raise_()

        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.log_dock)
        self.log_dock.setTitleBarWidget(self.log_panel.take_title_bar_widget())
        self.console_toggle_view_action = self.log_dock.toggleViewAction()
        self.console_toggle_view_action.setText("控制台")
        self.log_panel.expand_requested.connect(self._toggle_log_dock_expanded)
        self.log_panel.hide_requested.connect(self._hide_log_dock)
        self.log_panel.close_requested.connect(self._close_log_dock)
        self.log_dock.topLevelChanged.connect(self._sync_log_dock_controls)
        self.log_dock.visibilityChanged.connect(self._sync_log_dock_controls)
        self.log_panel.set_expanded(False)

        self.resizeDocks([self.connection_dock, self.model_dock], [450, 320], QtCore.Qt.Horizontal)
        self.resizeDocks([self.log_dock], [210], QtCore.Qt.Vertical)
        self._ensure_left_sidebar_visibility()

        self._populate_window_menu()

    def _make_connection_view(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.record_card = QtWidgets.QFrame()
        self.record_card.setObjectName("recordCard")
        record_layout = QtWidgets.QVBoxLayout(self.record_card)
        record_layout.setContentsMargins(12, 10, 12, 10)
        record_layout.setSpacing(6)

        record_header = QtWidgets.QHBoxLayout()
        record_header.setContentsMargins(0, 0, 0, 0)
        self.record_title_label = QtWidgets.QLabel("数据录制")
        self.record_title_label.setObjectName("sectionTitle")
        self.record_btn = QtWidgets.QPushButton("开始录制")
        record_btn_width = self.fontMetrics().horizontalAdvance("停止录制") + 30
        self.record_btn.setMinimumWidth(record_btn_width)
        record_header.addWidget(self.record_title_label)
        record_header.addStretch(1)
        record_header.addWidget(self.record_btn)

        self.record_path_label = QtWidgets.QLabel()
        self.record_path_label.setObjectName("statusHint")
        self.record_path_label.setMinimumHeight(20)
        self.record_path_label.setWordWrap(False)
        self._set_record_path_text("未选择 CSV 文件")

        record_layout.addLayout(record_header)
        record_layout.addWidget(self.record_path_label)

        layout.addWidget(self.serial_panel)
        layout.addWidget(self.record_card)
        layout.addStretch(1)
        return self._wrap_scroll_area(container)

    def _make_control_view(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        layout.addWidget(self.command_panel)
        layout.addWidget(self.preset_command_panel)
        layout.addStretch(1)
        return self._wrap_scroll_area(container)

    def _create_plot_placeholder(self):
        placeholder = QtWidgets.QFrame()
        placeholder.setObjectName("plotPlaceholder")
        layout = QtWidgets.QVBoxLayout(placeholder)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        title = QtWidgets.QLabel("波形图已切换到独立窗口")
        title.setObjectName("sectionTitle")
        title.setAlignment(QtCore.Qt.AlignCenter)

        hint = QtWidgets.QLabel("可以在顶部“波形”菜单中切换全屏/悬浮窗，或直接点下方按钮恢复嵌入。")
        hint.setObjectName("statusHint")
        hint.setAlignment(QtCore.Qt.AlignCenter)
        hint.setWordWrap(True)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)
        button_row.setAlignment(QtCore.Qt.AlignCenter)

        self.restore_wave_btn = QtWidgets.QPushButton("恢复嵌入")
        self.wave_fullscreen_placeholder_btn = QtWidgets.QPushButton("波形全屏")
        button_row.addWidget(self.restore_wave_btn)
        button_row.addWidget(self.wave_fullscreen_placeholder_btn)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(button_row)

        self.restore_wave_btn.clicked.connect(self._restore_waveform_embedded)
        self.wave_fullscreen_placeholder_btn.clicked.connect(self._show_waveform_fullscreen)
        return placeholder

    def _set_app_icon(self):
        if not APP_ICON_PATH.exists():
            return
        icon = QtGui.QIcon(str(APP_ICON_PATH))
        if icon.isNull():
            return
        self.setWindowIcon(icon)

    def _ensure_welcome_dialog(self):
        if self._welcome_dialog is None:
            self._welcome_dialog = WelcomeDialog(self.cfg, self.windowIcon(), self)
            self._welcome_dialog.show_on_startup_changed.connect(self._set_show_welcome_on_startup)
            self._welcome_dialog.open_device_requested.connect(lambda: self._focus_dock(self.connection_dock))
            self._welcome_dialog.open_control_requested.connect(lambda: self._focus_dock(self.control_dock))
            self._welcome_dialog.open_wave_requested.connect(self._focus_wave_workspace)
            self._welcome_dialog.open_model_requested.connect(lambda: self._focus_dock(self.model_dock))
        self._welcome_dialog.set_show_on_startup(self._show_welcome_on_startup)
        return self._welcome_dialog

    def _set_show_welcome_on_startup(self, enabled: bool):
        self._show_welcome_on_startup = bool(enabled)
        if hasattr(self, "show_welcome_on_startup_action"):
            blocker = QtCore.QSignalBlocker(self.show_welcome_on_startup_action)
            self.show_welcome_on_startup_action.setChecked(self._show_welcome_on_startup)
            del blocker
        if self._welcome_dialog is not None:
            self._welcome_dialog.set_show_on_startup(self._show_welcome_on_startup)
        self._save_persistent_settings()

    def _show_welcome_page(self, force: bool = False):
        if not force and self._welcome_seen and not self._show_welcome_on_startup:
            return
        dialog = self._ensure_welcome_dialog()
        first_launch = not self._welcome_seen
        dialog.set_context(
            theme_text=self.theme_combo.currentText() if hasattr(self, "theme_combo") else THEME_PRESETS[DEFAULT_THEME_KEY]["label"],
            model_text=self.model_panel.model_combo.currentText() if hasattr(self.model_panel, "model_combo") else "--",
            scene_text=self.model_panel.mode_combo.currentText() if hasattr(self.model_panel, "mode_combo") else "--",
            show_on_startup=self._show_welcome_on_startup,
            first_launch=first_launch,
        )
        if not dialog.isVisible():
            dialog.adjustSize()
            center = self.frameGeometry().center() - dialog.rect().center()
            dialog.move(center)
            dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        if first_launch:
            self._welcome_seen = True
            self._save_persistent_settings()

    def _focus_dock(self, dock: QtWidgets.QDockWidget):
        if dock is None:
            return
        dock.show()
        dock.raise_()
        self.activateWindow()

    def _sync_log_dock_controls(self, *_args):
        if not hasattr(self, "log_dock") or not hasattr(self, "log_panel"):
            return
        self.log_panel.set_expanded(self.log_dock.isFloating())

    def _show_log_dock(self):
        if not hasattr(self, "log_dock"):
            return
        if self.log_dock.isHidden():
            self._restore_log_dock_embedded(focus=True)
            self.statusBar().showMessage("控制台已恢复显示", 2500)
            return
        self.log_dock.show()
        self.log_dock.raise_()
        self.log_panel.console.setFocus(QtCore.Qt.OtherFocusReason)
        self.activateWindow()

    def _restore_log_dock_embedded(self, focus: bool = False):
        if not hasattr(self, "log_dock"):
            return
        self._console_dock_restoring = True
        try:
            if self.log_dock.isFloating():
                self.log_dock.showNormal()
                self.log_dock.setFloating(False)
            if self.dockWidgetArea(self.log_dock) == QtCore.Qt.NoDockWidgetArea:
                self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.log_dock)
            self.log_dock.show()
            self.resizeDocks([self.log_dock], [210], QtCore.Qt.Vertical)
            if focus:
                self.log_panel.console.setFocus(QtCore.Qt.OtherFocusReason)
                self._focus_dock(self.log_dock)
        finally:
            self._console_dock_restoring = False
            self._sync_log_dock_controls()

    def _toggle_log_dock_expanded(self):
        if not hasattr(self, "log_dock"):
            return
        if self.log_dock.isFloating():
            self._restore_log_dock_embedded(focus=True)
            return
        self.log_dock.show()
        self.log_dock.setFloating(True)
        self.log_dock.resize(max(self.width() - 120, 1000), max(self.height() - 160, 360))
        self.log_dock.showMaximized()
        self.log_panel.console.setFocus(QtCore.Qt.OtherFocusReason)
        self._sync_log_dock_controls()

    def _hide_log_dock(self):
        if not hasattr(self, "log_dock"):
            return
        self._restore_log_dock_embedded(focus=False)
        self.log_dock.hide()
        self.statusBar().showMessage("控制台已隐藏，可点击顶部工具栏“控制台”重新显示", 3500)
        self._sync_log_dock_controls()

    def _close_log_dock(self):
        if not hasattr(self, "log_dock"):
            return
        if self.log_dock.isFloating():
            self._restore_log_dock_embedded(focus=False)
            self.statusBar().showMessage("控制台已还原为底部嵌入视图", 2500)
        else:
            self._restore_log_dock_embedded(focus=True)
            self.statusBar().showMessage("控制台当前已是底部嵌入视图", 2500)
        self._sync_log_dock_controls()

    def _focus_wave_workspace(self):
        self._restore_waveform_embedded()
        self.plot_panel.setFocus(QtCore.Qt.OtherFocusReason)
        self.activateWindow()

    def _show_about_dialog(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"关于 {self.cfg.app_name}")
        dialog.setModal(True)
        dialog.resize(560, 420)
        if not self.windowIcon().isNull():
            dialog.setWindowIcon(self.windowIcon())

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        header_row = QtWidgets.QHBoxLayout()
        header_row.setSpacing(14)

        icon_label = QtWidgets.QLabel()
        icon_label.setFixedSize(72, 72)
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        if not self.windowIcon().isNull():
            icon_label.setPixmap(self.windowIcon().pixmap(72, 72))
        header_row.addWidget(icon_label, 0, QtCore.Qt.AlignTop)

        title_layout = QtWidgets.QVBoxLayout()
        title_layout.setSpacing(4)
        title_label = QtWidgets.QLabel(self.cfg.app_name)
        title_label.setObjectName("sectionTitle")
        title_label.setWordWrap(True)
        subtitle_label = QtWidgets.QLabel(self.cfg.app_tagline)
        subtitle_label.setObjectName("statusHint")
        subtitle_label.setWordWrap(True)
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        header_row.addLayout(title_layout, 1)
        layout.addLayout(header_row)

        info_card = QtWidgets.QFrame()
        info_card.setObjectName("recordCard")
        info_layout = QtWidgets.QFormLayout(info_card)
        info_layout.setContentsMargins(14, 14, 14, 14)
        info_layout.setHorizontalSpacing(18)
        info_layout.setVerticalSpacing(10)
        info_layout.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        info_layout.addRow("软件名称", QtWidgets.QLabel(self.cfg.app_name))
        info_layout.addRow("版本", QtWidgets.QLabel(self.cfg.app_version))
        info_layout.addRow("作者", QtWidgets.QLabel(self.cfg.app_author))
        info_layout.addRow("软件定位", QtWidgets.QLabel(self.cfg.app_tagline))
        info_layout.addRow("核心能力", QtWidgets.QLabel("串口联调、波形分析、3D 仿真、模型导入、主题切换"))
        info_layout.addRow("使用方式", QtWidgets.QLabel("打开 EXE 后按欢迎页或软件内说明完成连接、启动与观察"))
        layout.addWidget(info_card)

        desc_label = QtWidgets.QLabel(
            "本软件面向控制算法调试与被控对象仿真联调，支持串口通信、波形观察、3D 场景监视与运行参数配置。"
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec_()

    def _wrap_scroll_area(self, widget: QtWidgets.QWidget):
        area = QtWidgets.QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QtWidgets.QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        area.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        area.setAlignment(QtCore.Qt.AlignTop)
        content_width = max(widget.minimumSizeHint().width(), widget.sizeHint().width(), 260)
        widget.setMinimumWidth(content_width)
        area.setMinimumWidth(content_width + 18)
        area.setWidget(widget)
        return area

    def _calculate_sidebar_target_width(self, *views: QtWidgets.QWidget) -> int:
        width_candidates = []
        for view in views:
            if view is None:
                continue
            content = view.widget() if isinstance(view, QtWidgets.QScrollArea) else view
            if content is None:
                continue
            width_candidates.append(max(content.minimumSizeHint().width(), content.sizeHint().width()))
            width_candidates.append(max(view.minimumSizeHint().width(), view.sizeHint().width()))
        baseline = max(width_candidates or [360]) + 28
        screen_limit = max(360, int(self.width() * 0.34))
        return max(360, min(baseline, screen_limit))

    def _ensure_left_sidebar_visibility(self):
        if not hasattr(self, "connection_dock"):
            return
        target_width = max(int(self._left_sidebar_target_width or 0), 360)
        current_width = max(self.connection_dock.width(), self.control_dock.width(), self.channel_dock.width())
        if current_width >= target_width:
            return
        for dock in (self.connection_dock, self.control_dock, self.channel_dock):
            dock.resize(target_width, dock.height())
        self.resizeDocks(
            [self.connection_dock, self.model_dock],
            [target_width, max(self.model_dock.width(), 300)],
            QtCore.Qt.Horizontal,
        )

    def _create_dock(self, title: str, widget: QtWidgets.QWidget, name: str):
        dock = QtWidgets.QDockWidget(title, self)
        dock.setObjectName(name)
        dock.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFloatable
        )
        dock.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea | QtCore.Qt.BottomDockWidgetArea
        )
        dock.setWidget(widget)
        return dock

    def _build_top_navigation(self):
        self.model_panel.set_embedded_controls_visible(False)

        self.refresh_ports_action = QtWidgets.QAction("刷新端口", self)
        self.refresh_ports_action.triggered.connect(self._refresh_ports)

        self.connect_serial_action = QtWidgets.QAction("连接", self)
        self.connect_serial_action.triggered.connect(self._connect_selected_port)

        self.disconnect_serial_action = QtWidgets.QAction("断开", self)
        self.disconnect_serial_action.triggered.connect(self.close_serial_signal.emit)

        self.run_action = QtWidgets.QAction("启动", self)
        self.run_action.triggered.connect(lambda: self._send_toolbar_command("RUN 1"))

        self.stop_action = QtWidgets.QAction("停止", self)
        self.stop_action.triggered.connect(lambda: self._send_toolbar_command("RUN 0"))

        self.get_status_action = QtWidgets.QAction("读取状态", self)
        self.get_status_action.triggered.connect(lambda: self._send_toolbar_command("GET STATUS"))

        self.record_action = QtWidgets.QAction("开始录制", self)
        self.record_action.triggered.connect(self._toggle_record)

        self.load_settings_action = QtWidgets.QAction("加载设置...", self)
        self.load_settings_action.triggered.connect(self._load_settings_via_dialog)
        self.export_settings_action = QtWidgets.QAction("导出设置...", self)
        self.export_settings_action.triggered.connect(self._export_settings_via_dialog)
        self.reset_settings_action = QtWidgets.QAction("重置设置", self)
        self.reset_settings_action.triggered.connect(self._reset_user_settings)

        self.follow_view_action = QtWidgets.QAction("视角跟随", self)
        self.follow_view_action.setCheckable(True)
        self.follow_view_action.setChecked(self.model_panel.is_follow_enabled())
        self.follow_view_action.toggled.connect(self.model_panel.set_follow_enabled)
        self.model_panel.follow_cb.toggled.connect(self.follow_view_action.setChecked)

        self.wave_pan_left_action = QtWidgets.QAction("左移视图", self)
        self.wave_pan_left_action.triggered.connect(lambda: self.plot_panel._pan_x(-0.35))
        self.wave_pan_right_action = QtWidgets.QAction("右移视图", self)
        self.wave_pan_right_action.triggered.connect(lambda: self.plot_panel._pan_x(0.35))
        self.wave_zoom_in_action = QtWidgets.QAction("时间放大", self)
        self.wave_zoom_in_action.triggered.connect(lambda: self.plot_panel._change_window(0.8))
        self.wave_zoom_out_action = QtWidgets.QAction("时间缩小", self)
        self.wave_zoom_out_action.triggered.connect(lambda: self.plot_panel._change_window(1.25))
        self.wave_back_action = QtWidgets.QAction("后退视图", self)
        self.wave_back_action.triggered.connect(lambda: self.plot_panel.navigate_view_history(-1))
        self.wave_forward_action = QtWidgets.QAction("前进视图", self)
        self.wave_forward_action.triggered.connect(lambda: self.plot_panel.navigate_view_history(1))
        self.wave_latest_action = QtWidgets.QAction("回到最新", self)
        self.wave_latest_action.triggered.connect(self.plot_panel.focus_latest)
        self.wave_focus_action = QtWidgets.QAction("一键聚焦", self)
        self.wave_focus_action.triggered.connect(self.plot_panel.focus_current_view)
        self.wave_fit_y_action = QtWidgets.QAction("适配 Y 轴", self)
        self.wave_fit_y_action.triggered.connect(self.plot_panel.fit_y_to_visible)
        self.wave_export_image_action = QtWidgets.QAction("导出图片", self)
        self.wave_export_image_action.triggered.connect(self.plot_panel.export_plot_image)
        self.wave_export_csv_action = QtWidgets.QAction("导出 CSV", self)
        self.wave_export_csv_action.triggered.connect(self.plot_panel.export_visible_csv)
        self.wave_clear_labels_action = QtWidgets.QAction("清空标签", self)
        self.wave_clear_labels_action.triggered.connect(self.plot_panel.clear_point_markers)
        self.wave_popout_action = QtWidgets.QAction("波形悬浮窗", self)
        self.wave_popout_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+P"))
        self.wave_popout_action.triggered.connect(self._show_waveform_popout)
        self.wave_fullscreen_action = QtWidgets.QAction("波形全屏", self)
        self.wave_fullscreen_action.setShortcut(QtGui.QKeySequence("F11"))
        self.wave_fullscreen_action.triggered.connect(self._show_waveform_fullscreen)
        self.wave_restore_embed_action = QtWidgets.QAction("恢复嵌入", self)
        self.wave_restore_embed_action.triggered.connect(self._restore_waveform_embedded)
        self.wave_capture_a_action = QtWidgets.QAction("游标 A 到当前", self)
        self.wave_capture_a_action.triggered.connect(lambda: self.plot_panel._capture_measure_cursor("a"))
        self.wave_capture_b_action = QtWidgets.QAction("游标 B 到当前", self)
        self.wave_capture_b_action.triggered.connect(lambda: self.plot_panel._capture_measure_cursor("b"))
        self.wave_reset_measure_action = QtWidgets.QAction("重置测量游标", self)
        self.wave_reset_measure_action.triggered.connect(self.plot_panel._reset_measurement_lines)

        self.wave_cursor_action = QtWidgets.QAction("十字光标", self)
        self.wave_cursor_action.setCheckable(True)
        self.wave_cursor_action.setChecked(self.plot_panel.is_cursor_enabled())
        self.wave_cursor_action.toggled.connect(self.plot_panel.set_cursor_enabled)
        self.plot_panel.cursor_cb.toggled.connect(self.wave_cursor_action.setChecked)

        self.wave_annotation_action = QtWidgets.QAction("点击标记", self)
        self.wave_annotation_action.setCheckable(True)
        self.wave_annotation_action.setChecked(self.plot_panel.is_annotation_enabled())
        self.wave_annotation_action.toggled.connect(self.plot_panel.set_annotation_enabled)
        self.plot_panel.annotation_cb.toggled.connect(self.wave_annotation_action.setChecked)

        self.wave_measurement_action = QtWidgets.QAction("双游标测量", self)
        self.wave_measurement_action.setCheckable(True)
        self.wave_measurement_action.setChecked(self.plot_panel.is_measurement_enabled())
        self.wave_measurement_action.toggled.connect(self.plot_panel.set_measurement_enabled)
        self.plot_panel.measurement_cb.toggled.connect(self.wave_measurement_action.setChecked)

        self.wave_mouse_group = QtWidgets.QActionGroup(self)
        self.wave_mouse_pan_action = QtWidgets.QAction("平移拖拽", self)
        self.wave_mouse_pan_action.setCheckable(True)
        self.wave_mouse_rect_action = QtWidgets.QAction("框选缩放", self)
        self.wave_mouse_rect_action.setCheckable(True)
        self.wave_mouse_group.addAction(self.wave_mouse_pan_action)
        self.wave_mouse_group.addAction(self.wave_mouse_rect_action)
        self.wave_mouse_pan_action.triggered.connect(lambda: self.plot_panel.set_mouse_mode_key("pan"))
        self.wave_mouse_rect_action.triggered.connect(lambda: self.plot_panel.set_mouse_mode_key("rect"))

        self.show_welcome_action = QtWidgets.QAction("欢迎页", self)
        self.show_welcome_action.triggered.connect(lambda: self._show_welcome_page(force=True))
        self.show_welcome_on_startup_action = QtWidgets.QAction("启动时显示欢迎页", self)
        self.show_welcome_on_startup_action.setCheckable(True)
        self.show_welcome_on_startup_action.setChecked(self._show_welcome_on_startup)
        self.show_welcome_on_startup_action.toggled.connect(self._set_show_welcome_on_startup)
        self.about_action = QtWidgets.QAction("关于", self)
        self.about_action.triggered.connect(self._show_about_dialog)
        self.show_console_action = QtWidgets.QAction("控制台", self)
        self.show_console_action.setToolTip("显示并聚焦控制台")
        self.show_console_action.triggered.connect(self._show_log_dock)

        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)

        self.file_menu = menu_bar.addMenu("文件")
        self.file_menu.addAction(self.record_action)
        self.file_menu.addSeparator()
        self.exit_action = self.file_menu.addAction("退出")
        self.exit_action.triggered.connect(self.close)

        self.settings_menu = menu_bar.addMenu("设置")
        self.theme_menu = self.settings_menu.addMenu("主题")
        self._theme_menu_action_group = QtWidgets.QActionGroup(self)
        self._theme_menu_action_group.setExclusive(True)
        for theme_key in THEME_ORDER:
            theme_action = self.theme_menu.addAction(THEME_PRESETS[theme_key]["label"])
            theme_action.setCheckable(True)
            theme_action.setData(theme_key)
            self._theme_menu_action_group.addAction(theme_action)
        self._theme_menu_action_group.triggered.connect(self._on_theme_menu_triggered)
        self.settings_menu.addSeparator()
        self.settings_menu.addAction(self.load_settings_action)
        self.settings_menu.addAction(self.export_settings_action)
        self.settings_menu.addSeparator()
        self.settings_menu.addAction(self.reset_settings_action)

        self.model_menu = menu_bar.addMenu("模型")
        self.model_selector_menu = self.model_menu.addMenu("切换模型")
        self.model_menu.addSeparator()
        self.model_menu.addAction(self.model_panel.import_model_action)
        self.model_menu.addAction(self.model_panel.use_default_action)
        self.model_menu.addSeparator()
        self.model_menu.addAction(self.model_panel.choose_builtin_primary_action)
        self.model_menu.addAction(self.model_panel.choose_builtin_accent_action)
        self.model_menu.addAction(self.model_panel.reset_builtin_colors_action)
        self.model_menu.addSeparator()
        self.model_menu.addAction(self.model_panel.external_pose_dialog_action)
        self.model_menu.addAction(self.model_panel.external_material_dialog_action)

        self.scene_menu = menu_bar.addMenu("场景")
        self.scene_selector_menu = self.scene_menu.addMenu("切换场景")
        self.scene_menu.addSeparator()
        self.scene_menu.addAction(self.follow_view_action)

        self.wave_menu = menu_bar.addMenu("波形")
        self._populate_wave_menu(self.wave_menu)

        self.view_menu = menu_bar.addMenu("视图")
        self.view_menu.addAction(self.model_panel.reset_view_action)
        self.view_menu.addAction(self.model_panel.clear_trail_action)

        self.window_menu = menu_bar.addMenu("窗口")
        self.show_views_menu = self.window_menu.addMenu("显示视图")
        self.reset_layout_action = self.window_menu.addAction("恢复默认布局")
        self.reset_layout_action.triggered.connect(self._restore_default_layout)
        self.window_menu.addAction(self.show_console_action)

        self.help_menu = menu_bar.addMenu("帮助")
        self.help_menu.addAction(self.show_welcome_action)
        self.help_menu.addAction(self.show_welcome_on_startup_action)
        self.help_menu.addAction(self.about_action)

        self.workbench_toolbar = QtWidgets.QToolBar("工作台工具栏")
        self.workbench_toolbar.setObjectName("workbench_toolbar")
        self.workbench_toolbar.setMovable(False)
        self.workbench_toolbar.setFloatable(False)
        self.workbench_toolbar.setIconSize(QtCore.QSize(16, 16))
        self.workbench_toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.workbench_toolbar)

        self.model_selector_btn = QtWidgets.QToolButton()
        self.model_selector_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.model_selector_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.model_selector_btn.setMenu(self.model_selector_menu)

        self.scene_selector_btn = QtWidgets.QToolButton()
        self.scene_selector_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.scene_selector_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.scene_selector_btn.setMenu(self.scene_selector_menu)

        self.wave_menu_btn = QtWidgets.QToolButton()
        self.wave_menu_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.wave_menu_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.wave_menu_btn.setText("波形")
        self.wave_menu_btn.setMenu(self.wave_menu)

        self.wave_window_menu = QtWidgets.QMenu(self)
        self._populate_wave_window_menu(self.wave_window_menu)
        self.wave_window_btn = QtWidgets.QToolButton()
        self.wave_window_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.wave_window_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.wave_window_btn.setText("波形窗口")
        self.wave_window_btn.setMenu(self.wave_window_menu)

        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.theme_combo.setMinimumContentsLength(8)
        self.theme_combo.setToolTip("切换当前界面主题")
        for theme_key in THEME_ORDER:
            self.theme_combo.addItem(THEME_PRESETS[theme_key]["label"], theme_key)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)

        self.workbench_toolbar.addAction(self.refresh_ports_action)
        self.workbench_toolbar.addAction(self.connect_serial_action)
        self.workbench_toolbar.addAction(self.disconnect_serial_action)
        self.workbench_toolbar.addSeparator()
        self.workbench_toolbar.addAction(self.run_action)
        self.workbench_toolbar.addAction(self.stop_action)
        self.workbench_toolbar.addAction(self.get_status_action)
        self.workbench_toolbar.addAction(self.record_action)
        self.workbench_toolbar.addSeparator()
        self.workbench_toolbar.addWidget(self.model_selector_btn)
        self.workbench_toolbar.addWidget(self.scene_selector_btn)
        self.workbench_toolbar.addWidget(self.wave_menu_btn)
        self.workbench_toolbar.addWidget(self.wave_window_btn)
        self.workbench_toolbar.addWidget(self.theme_combo)
        self.workbench_toolbar.addAction(self.show_console_action)
        self.workbench_toolbar.addAction(self.follow_view_action)
        self.workbench_toolbar.addAction(self.model_panel.reset_view_action)
        self.workbench_toolbar.addAction(self.model_panel.clear_trail_action)
        self.workbench_toolbar.addSeparator()
        self.workbench_toolbar.addWidget(self.model_panel.action_menu_btn)

        self.statusBar().showMessage("Eclipse 风格工作台布局已加载")
        self.model_summary_label = QtWidgets.QLabel()
        self.statusBar().addPermanentWidget(self.model_summary_label)

        self.model_panel.model_combo.currentIndexChanged.connect(self._sync_navigation_state)
        self.model_panel.mode_combo.currentIndexChanged.connect(self._sync_navigation_state)
        self.model_panel.follow_cb.toggled.connect(self._update_3d_status_summary)
        self.model_panel.import_model_action.triggered.connect(self._schedule_navigation_refresh)
        self.model_panel.use_default_action.triggered.connect(self._schedule_navigation_refresh)
        self.plot_panel.mouse_mode_combo.currentIndexChanged.connect(self._sync_wave_actions)
        self.plot_panel.measure_channel_combo.currentIndexChanged.connect(self._sync_wave_actions)
        self.plot_panel.measurement_cb.toggled.connect(self._sync_wave_actions)
        self.plot_panel.annotation_cb.toggled.connect(self._sync_wave_actions)
        self.plot_panel.cursor_cb.toggled.connect(self._sync_wave_actions)
        self._sync_wave_actions()
        self._sync_wave_window_actions()
        self._sync_theme_controls()

    def _populate_window_menu(self):
        self.show_views_menu.clear()
        for dock, label in (
            (self.connection_dock, "设备"),
            (self.control_dock, "控制"),
            (self.channel_dock, "通道"),
            (self.model_dock, "3D 视图"),
            (self.status_dock, "运行状态"),
            (self.log_dock, "控制台"),
        ):
            action = dock.toggleViewAction()
            action.setText(label)
            self.show_views_menu.addAction(action)
        self.window_menu.addSeparator()
        toolbar_action = self.workbench_toolbar.toggleViewAction()
        toolbar_action.setText("工作台工具栏")
        self.window_menu.addAction(toolbar_action)

    def _populate_wave_menu(self, menu: QtWidgets.QMenu):
        menu.clear()

        nav_menu = menu.addMenu("导航")
        nav_menu.addAction(self.wave_pan_left_action)
        nav_menu.addAction(self.wave_pan_right_action)
        nav_menu.addSeparator()
        nav_menu.addAction(self.wave_zoom_in_action)
        nav_menu.addAction(self.wave_zoom_out_action)
        nav_menu.addSeparator()
        nav_menu.addAction(self.wave_back_action)
        nav_menu.addAction(self.wave_forward_action)
        nav_menu.addSeparator()
        nav_menu.addAction(self.wave_latest_action)
        nav_menu.addAction(self.wave_focus_action)
        nav_menu.addAction(self.wave_fit_y_action)

        interact_menu = menu.addMenu("交互")
        mouse_menu = interact_menu.addMenu("鼠标模式")
        mouse_menu.addAction(self.wave_mouse_pan_action)
        mouse_menu.addAction(self.wave_mouse_rect_action)
        interact_menu.addAction(self.wave_cursor_action)
        interact_menu.addAction(self.wave_annotation_action)
        interact_menu.addAction(self.wave_clear_labels_action)

        measure_menu = menu.addMenu("测量")
        measure_menu.addAction(self.wave_measurement_action)
        self.wave_measure_channel_menu = measure_menu.addMenu("测量通道")
        measure_menu.addSeparator()
        measure_menu.addAction(self.wave_capture_a_action)
        measure_menu.addAction(self.wave_capture_b_action)
        measure_menu.addAction(self.wave_reset_measure_action)

        export_menu = menu.addMenu("导出")
        export_menu.addAction(self.wave_export_image_action)
        export_menu.addAction(self.wave_export_csv_action)

        menu.addSeparator()
        window_menu = menu.addMenu("窗口")
        self._populate_wave_window_menu(window_menu)

        self._rebuild_wave_measure_channel_menu()

    def _populate_wave_window_menu(self, menu: QtWidgets.QMenu):
        menu.clear()
        menu.addAction(self.wave_popout_action)
        menu.addAction(self.wave_fullscreen_action)
        menu.addSeparator()
        menu.addAction(self.wave_restore_embed_action)

    def _ensure_waveform_window(self):
        if self._waveform_window is None:
            self._waveform_window = WaveformDetachedWindow(self)
            self._waveform_window.close_requested.connect(self._restore_waveform_embedded)
        return self._waveform_window

    def _show_waveform_popout(self):
        self._detach_waveform("floating")

    def _show_waveform_fullscreen(self):
        self._detach_waveform("fullscreen")

    def _detach_waveform(self, mode: str):
        window = self._ensure_waveform_window()
        if self.plot_panel.parentWidget() is self.central_host:
            self.central_layout.removeWidget(self.plot_panel)
        elif self.plot_panel.parentWidget() is window:
            window.layout().removeWidget(self.plot_panel)

        window.layout().addWidget(self.plot_panel)
        self.plot_placeholder.show()
        self._waveform_window_mode = mode
        window.apply_display_mode(mode)

        if mode == "fullscreen":
            window.setWindowTitle("波形全屏")
            window.showMaximized()
        else:
            window.setWindowTitle("波形悬浮窗")
            window.resize(max(window.width(), 1080), max(window.height(), 680))
            window.show()

        window.raise_()
        window.activateWindow()
        self._sync_wave_window_actions()
        self.statusBar().showMessage("波形图已切换到独立窗口", 2500)

    def _restore_waveform_embedded(self):
        if self._waveform_window_mode is None:
            return
        window = self._waveform_window
        if window is not None and self.plot_panel.parentWidget() is window:
            window.layout().removeWidget(self.plot_panel)
            window.hide()
        self.central_layout.insertWidget(0, self.plot_panel, 1)
        self.plot_placeholder.hide()
        self._waveform_window_mode = None
        self._sync_wave_window_actions()
        self.statusBar().showMessage("波形图已恢复到主界面", 2500)

    def _rebuild_wave_measure_channel_menu(self):
        self.wave_measure_channel_menu.clear()
        self._wave_measure_group = QtWidgets.QActionGroup(self.wave_measure_channel_menu)
        self._wave_measure_group.setExclusive(True)
        current_channel = self.plot_panel.current_measure_channel()
        for label, channel_name in self.plot_panel.measurement_channel_items():
            action = self.wave_measure_channel_menu.addAction(label)
            action.setCheckable(True)
            action.setData(channel_name)
            action.setChecked(channel_name == current_channel)
            self._wave_measure_group.addAction(action)
        self._wave_measure_group.triggered.connect(self._on_wave_measure_channel_triggered)

    def _on_wave_measure_channel_triggered(self, action: QtWidgets.QAction):
        channel_name = action.data()
        if channel_name:
            self.plot_panel.set_measure_channel(channel_name)

    def _sync_wave_actions(self):
        mode_key = self.plot_panel.current_mouse_mode()
        self.wave_mouse_pan_action.setChecked(mode_key == "pan")
        self.wave_mouse_rect_action.setChecked(mode_key == "rect")
        self.wave_capture_a_action.setEnabled(self.plot_panel.is_measurement_enabled())
        self.wave_capture_b_action.setEnabled(self.plot_panel.is_measurement_enabled())
        self.wave_reset_measure_action.setEnabled(self.plot_panel.is_measurement_enabled())
        self._rebuild_wave_measure_channel_menu()

    def _sync_wave_window_actions(self):
        detached = self._waveform_window_mode is not None
        fullscreen = self._waveform_window_mode == "fullscreen"
        self.wave_popout_action.setText("切换为小窗" if fullscreen else "波形悬浮窗")
        self.wave_fullscreen_action.setText("波形全屏中" if fullscreen else "波形全屏")
        self.wave_popout_action.setEnabled(True)
        self.wave_fullscreen_action.setEnabled(not fullscreen)
        self.wave_restore_embed_action.setEnabled(detached)
        if hasattr(self, "wave_window_btn"):
            if fullscreen:
                self.wave_window_btn.setText("波形全屏中")
            elif detached:
                self.wave_window_btn.setText("波形小窗中")
            else:
                self.wave_window_btn.setText("波形窗口")
        if hasattr(self, "restore_wave_btn"):
            self.restore_wave_btn.setEnabled(detached)
        if hasattr(self, "wave_fullscreen_placeholder_btn"):
            self.wave_fullscreen_placeholder_btn.setEnabled(detached)

    def _theme_preset(self, theme_key: str) -> dict:
        return THEME_PRESETS.get(theme_key, THEME_PRESETS[DEFAULT_THEME_KEY])

    def _sync_theme_controls(self):
        if hasattr(self, "theme_combo"):
            blocker = QtCore.QSignalBlocker(self.theme_combo)
            index = self.theme_combo.findData(self._theme_key)
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)
            del blocker
        if hasattr(self, "_theme_menu_action_group"):
            for action in self._theme_menu_action_group.actions():
                action.setChecked(action.data() == self._theme_key)

    def _on_theme_menu_triggered(self, action: QtWidgets.QAction):
        theme_key = action.data()
        if theme_key:
            self._apply_theme(str(theme_key), user_selected=True)

    def _on_theme_combo_changed(self, index: int):
        if index < 0:
            return
        theme_key = self.theme_combo.itemData(index)
        if theme_key:
            self._apply_theme(str(theme_key), user_selected=True)

    def _apply_theme(
        self,
        theme_key: str,
        persist: bool = True,
        show_message: bool = True,
        user_selected: bool = False,
    ):
        theme_key = theme_key if theme_key in THEME_PRESETS else DEFAULT_THEME_KEY
        theme = self._theme_preset(theme_key)
        self._theme_key = theme_key
        if user_selected:
            self._theme_user_selected = True
        self._apply_workbench_style(theme)
        if hasattr(self, "plot_panel"):
            self.plot_panel.apply_theme(theme)
        if hasattr(self, "model_panel"):
            self.model_panel.apply_theme(theme)
        if hasattr(self, "model_summary_label"):
            self.model_summary_label.setStyleSheet(f"padding: 0 6px; color: {theme['summary_text']};")
        self._sync_theme_controls()
        if show_message:
            self.statusBar().showMessage(f"已切换主题: {theme['label']}", 2500)
        if persist:
            self._save_persistent_settings()

    def _apply_workbench_style(self, theme: dict):
        font = QtGui.QFont("Microsoft YaHei UI", 9)
        self.setFont(font)
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: %(window_bg)s; color: %(text)s; }
            QMenuBar {
                background: %(toolbar_bg)s;
                border-bottom: 1px solid %(border)s;
                color: %(text)s;
            }
            QMenuBar::item {
                padding: 5px 10px;
                background: transparent;
                border-radius: 4px;
            }
            QMenuBar::item:selected { background: %(menubar_hover)s; }
            QMenu {
                background: %(menu_bg)s;
                border: 1px solid %(border)s;
                padding: 4px;
                color: %(text)s;
            }
            QMenu::item { padding: 6px 18px; border-radius: 4px; }
            QMenu::item:selected { background: %(menu_hover)s; }
            QMenu::separator {
                height: 1px;
                background: %(separator)s;
                margin: 5px 10px;
            }
            QToolBar {
                background: %(toolbar_bg)s;
                border-bottom: 1px solid %(border)s;
                spacing: 4px;
                padding: 4px 6px;
            }
            QToolBar::separator {
                background: %(separator)s;
                width: 1px;
                margin: 4px 6px;
            }
            QPushButton, QToolButton {
                background: %(button_bg)s;
                border: 1px solid %(border_strong)s;
                border-radius: 6px;
                padding: 5px 10px;
                color: %(text)s;
            }
            QPushButton:hover, QToolButton:hover {
                background: %(button_hover)s;
                border-color: %(accent)s;
            }
            QPushButton:pressed, QToolButton:pressed { background: %(button_pressed)s; }
            QPushButton:disabled, QToolButton:disabled {
                color: %(disabled_text)s;
                background: %(disabled_bg)s;
                border-color: %(border)s;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
                background: %(input_bg)s;
                border: 1px solid %(border_strong)s;
                border-radius: 6px;
                padding: 5px 7px;
                selection-background-color: %(selection_bg)s;
            }
            QComboBox::drop-down { border: none; width: 22px; }
            QComboBox QAbstractItemView {
                background: %(menu_bg)s;
                border: 1px solid %(border)s;
                color: %(text)s;
                selection-background-color: %(selection_bg)s;
                selection-color: #ffffff;
            }
            QGroupBox {
                background: %(surface)s;
                border: 1px solid %(border)s;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: 600;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: %(group_title)s;
            }
            QDockWidget::title {
                background: %(dock_title_bg)s;
                border: 1px solid %(border)s;
                border-bottom: none;
                padding: 6px 10px;
                text-align: left;
                color: %(dock_title_text)s;
            }
            QWidget#dockTitleBar {
                background: %(dock_title_bg)s;
                border: 1px solid %(border)s;
                border-bottom: none;
            }
            QLabel#dockTitleText { color: %(dock_title_text)s; font-weight: 600; }
            QToolButton#dockTitleAction {
                padding: 3px 10px;
                min-height: 22px;
            }
            QMainWindow::separator { background: %(separator)s; width: 4px; height: 4px; }
            QScrollArea {
                border: none;
                background: %(scroll_bg)s;
            }
            QScrollBar:vertical {
                background: %(scroll_bg)s;
                width: 10px;
                margin: 6px 2px 6px 2px;
            }
            QScrollBar::handle:vertical {
                background: %(border_strong)s;
                min-height: 24px;
                border-radius: 5px;
            }
            QScrollBar:horizontal {
                background: %(scroll_bg)s;
                height: 10px;
                margin: 2px 6px 2px 6px;
            }
            QScrollBar::handle:horizontal {
                background: %(border_strong)s;
                min-width: 24px;
                border-radius: 5px;
            }
            QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {
                background: transparent;
                border: none;
            }
            QTabWidget::pane {
                border: 1px solid %(border)s;
                background: %(surface)s;
            }
            QTabBar::tab {
                background: %(tab_bg)s;
                color: %(tab_text)s;
                padding: 6px 12px;
                border: 1px solid %(border)s;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: %(tab_selected)s;
                color: %(title_text)s;
            }
            QTabBar::tab:hover { background: %(tab_hover)s; }
            QStatusBar {
                background: %(statusbar_bg)s;
                border-top: 1px solid %(border)s;
            }
            QStatusBar::item { border: none; }
            QLabel[statusKey="true"] { color: %(muted)s; }
            QLabel[statusValue="true"] { color: %(value_text)s; font-weight: 600; }
            QLabel#statusHint { color: %(muted)s; }
            QLabel#sectionTitle { font-weight: 700; color: %(title_text)s; }
            QFrame#recordCard {
                background: %(surface)s;
                border: 1px solid %(border)s;
                border-radius: 8px;
            }
            QFrame#presetRow {
                background: %(surface_alt)s;
                border: 1px solid %(border)s;
                border-radius: 8px;
            }
            QFrame#plotPlaceholder {
                background: %(placeholder_bg)s;
                border: 1px dashed %(placeholder_border)s;
                border-radius: 10px;
            }
            QPlainTextEdit#consoleView {
                background: %(console_bg)s;
                color: %(console_text)s;
                border: 1px solid %(border_strong)s;
                border-radius: 6px;
            }
            """ % theme
        )

    def _capture_default_layout(self):
        self._default_window_geometry = self.saveGeometry()
        self._default_window_state = self.saveState()

    def _restore_default_layout(self):
        self._restore_waveform_embedded()
        if self._default_window_state is None:
            return
        self.restoreState(self._default_window_state)
        self.connection_dock.show()
        self.control_dock.show()
        self.channel_dock.show()
        self.model_dock.show()
        self.status_dock.show()
        self.log_dock.show()
        self.connection_dock.raise_()
        self.model_dock.raise_()
        self._ensure_left_sidebar_visibility()
        self.statusBar().showMessage("已恢复默认工作台布局", 2500)

    def _serialize_byte_array(self, value: QtCore.QByteArray):
        return bytes(value.toBase64()).decode("ascii")

    def _deserialize_byte_array(self, value: str):
        if not value:
            return None
        try:
            return QtCore.QByteArray.fromBase64(value.encode("ascii"))
        except Exception:
            return None

    def _collect_settings_payload(self) -> dict:
        return {
            "version": 5,
            "theme": self._theme_key,
            "theme_user_selected": bool(self._theme_user_selected),
            "show_welcome_on_startup": bool(self._show_welcome_on_startup),
            "welcome_seen": bool(self._welcome_seen),
            "window": {
                "geometry": self._serialize_byte_array(self.saveGeometry()),
                "state": self._serialize_byte_array(self.saveState()),
            },
            "serial_panel": self.serial_panel.get_state(),
            "command_panel": self.command_panel.get_state(),
            "preset_panel": self.preset_command_panel.get_state(),
            "plot_panel": self.plot_panel.get_state(),
            "model_panel": self.model_panel.get_state(),
        }

    def _apply_settings_payload(self, payload: dict):
        if not isinstance(payload, dict):
            return

        payload_version = int(payload.get("version", 1) or 1)
        payload_theme = str(payload.get("theme", DEFAULT_THEME_KEY))
        theme_user_selected = payload.get("theme_user_selected", None)
        if theme_user_selected is None:
            # Migrate old settings: previous default was light; no explicit theme marker means use new ocean default.
            effective_theme = DEFAULT_THEME_KEY if payload_version < 3 and payload_theme == "light" else payload_theme
            self._theme_user_selected = bool(payload_version < 3 and payload_theme not in ("", "light"))
        else:
            effective_theme = payload_theme
            self._theme_user_selected = bool(theme_user_selected)
        self._show_welcome_on_startup = bool(payload.get("show_welcome_on_startup", True))
        welcome_seen = payload.get("welcome_seen", None)
        if welcome_seen is None:
            self._welcome_seen = not self._show_welcome_on_startup
        else:
            self._welcome_seen = bool(welcome_seen)
        if hasattr(self, "show_welcome_on_startup_action"):
            blocker = QtCore.QSignalBlocker(self.show_welcome_on_startup_action)
            self.show_welcome_on_startup_action.setChecked(self._show_welcome_on_startup)
            del blocker
        if self._welcome_dialog is not None:
            self._welcome_dialog.set_show_on_startup(self._show_welcome_on_startup)

        self._apply_theme(effective_theme, persist=False, show_message=False)
        self.serial_panel.apply_state(payload.get("serial_panel", {}))
        self.command_panel.apply_state(payload.get("command_panel", {}))
        self._apply_sim_period_ms(self.command_panel.current_sim_period_ms(), show_message=False)
        self.preset_command_panel.apply_state(payload.get("preset_panel", {}))
        self.plot_panel.apply_state(payload.get("plot_panel", {}))
        self.model_panel.apply_state(payload.get("model_panel", {}))
        self._sync_local_control_cache()

        window_state = payload.get("window", {})
        if isinstance(window_state, dict):
            geometry = self._deserialize_byte_array(str(window_state.get("geometry", "")))
            state = self._deserialize_byte_array(str(window_state.get("state", "")))
            if geometry is not None:
                self.restoreGeometry(geometry)
            if state is not None:
                self.restoreState(state)
        self._ensure_left_sidebar_visibility()

        self._sync_wave_actions()
        self._sync_navigation_state()
        self._sync_toolbar_state()
        self._update_3d_status_summary()

    def _write_settings_file(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._collect_settings_payload(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_settings_file(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def _settings_storage_path(self) -> Path:
        return USER_SETTINGS_PATH

    def _settings_dialog_root(self) -> Path:
        path = self._settings_storage_path().parent
        if path.exists():
            return path
        if LEGACY_USER_SETTINGS_PATH.exists():
            return LEGACY_USER_SETTINGS_PATH.parent
        return SOFTWARE_ROOT

    def _report_settings_save_error(self, path: Path, exc: Exception):
        message = f"设置保存失败: {path}"
        detail = str(exc).strip()
        if detail:
            message = f"{message} ({detail})"
        if message == self._settings_save_error:
            return
        self._settings_save_error = message
        if hasattr(self, "log_panel"):
            self.log_panel.append_line(f"[设置] {message}")
        self.statusBar().showMessage(message, 5000)

    def _save_persistent_settings(self):
        try:
            self._write_settings_file(self._settings_storage_path())
            self._settings_save_error = ""
        except Exception as exc:
            self._report_settings_save_error(self._settings_storage_path(), exc)

    def _load_persistent_settings(self):
        settings_path = self._settings_storage_path()
        if not settings_path.exists():
            return
        try:
            self._apply_settings_payload(self._read_settings_file(settings_path))
        except Exception as exc:
            self.statusBar().showMessage(f"已忽略损坏的本地设置文件: {settings_path} ({exc})", 5000)

    def _export_settings_via_dialog(self):
        default_name = f"ui_settings_{time.strftime('%Y%m%d_%H%M%S')}.json"
        target, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出设置",
            str(self._settings_dialog_root() / default_name),
            "JSON 文件 (*.json)",
        )
        if not target:
            return
        try:
            self._write_settings_file(Path(target))
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "导出失败", f"无法导出设置文件：\n{exc}")
            return
        self.statusBar().showMessage(f"设置已导出到 {target}", 3000)

    def _load_settings_via_dialog(self):
        source, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "加载设置",
            str(self._settings_dialog_root()),
            "JSON 文件 (*.json)",
        )
        if not source:
            return
        try:
            payload = self._read_settings_file(Path(source))
            self._apply_settings_payload(payload)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "加载失败", f"无法加载设置文件：\n{exc}")
            return
        self._save_persistent_settings()
        self.statusBar().showMessage(f"已加载设置: {source}", 3000)

    def _reset_user_settings(self):
        self._restore_waveform_embedded()
        self._set_simulation_running(False)
        self._theme_user_selected = False
        self._show_welcome_on_startup = True
        self._welcome_seen = False
        self._apply_theme(DEFAULT_THEME_KEY, persist=False, show_message=False)
        if hasattr(self, "show_welcome_on_startup_action"):
            blocker = QtCore.QSignalBlocker(self.show_welcome_on_startup_action)
            self.show_welcome_on_startup_action.setChecked(True)
            del blocker
        if self._welcome_dialog is not None:
            self._welcome_dialog.set_show_on_startup(True)
        self.serial_panel.reset_to_defaults()
        self.command_panel.reset_to_defaults()
        self.preset_command_panel.reset_to_defaults()
        self.plot_panel.reset_to_defaults()
        self.model_panel.reset_to_defaults()
        self._sync_local_control_cache()
        if self._default_window_geometry is not None:
            self.restoreGeometry(self._default_window_geometry)
        self._restore_default_layout()
        self._ensure_left_sidebar_visibility()
        self._sync_wave_actions()
        self._sync_navigation_state()
        self._sync_toolbar_state()
        self._update_3d_status_summary()
        self._save_persistent_settings()
        self.statusBar().showMessage("已重置为默认设置", 3000)

    def _setup_worker(self):
        self.worker_thread = QtCore.QThread(self)
        self.worker = SerialWorker(use_binary_tx=True)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        self.open_serial_signal.connect(self.worker.open)
        self.close_serial_signal.connect(self.worker.close)
        self.send_line_signal.connect(self.worker.send_line)
        self.send_feedback_signal.connect(self.worker.send_feedback)
        self.set_binary_signal.connect(self.worker.set_binary_tx)

        self.worker.telemetry_received.connect(self._on_telemetry)
        self.worker.line_received.connect(self._on_line)
        self.worker.comm_stats.connect(self._on_stats)
        self.worker.connection_changed.connect(self._on_connection_changed)
        self.worker.error.connect(self._append_log_error)

    def _setup_timers(self):
        self.sim_timer = QtCore.QTimer(self)
        self.sim_timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.sim_timer.timeout.connect(self._on_sim_tick)
        self._apply_sim_period_ms(self.command_panel.current_sim_period_ms(), show_message=False)

        self.ui_timer = QtCore.QTimer(self)
        self.ui_timer.setInterval(int(1000 / self.cfg.ui_refresh_hz))
        self.ui_timer.timeout.connect(self._update_timeout_state)
        self.ui_timer.start()

        self._last_sim_time = time.monotonic()

    def _schedule_navigation_refresh(self):
        QtCore.QTimer.singleShot(0, self._sync_navigation_state)

    def _sync_navigation_state(self):
        if hasattr(self, "_model_menu_action_group") and self._model_menu_action_group is not None:
            self._model_menu_action_group.deleteLater()
        if hasattr(self, "_scene_menu_action_group") and self._scene_menu_action_group is not None:
            self._scene_menu_action_group.deleteLater()

        self._model_menu_action_group = self._rebuild_combo_menu(
            self.model_selector_menu,
            self.model_panel.model_combo,
            self._on_model_menu_triggered,
        )
        self._scene_menu_action_group = self._rebuild_combo_menu(
            self.scene_selector_menu,
            self.model_panel.mode_combo,
            self._on_scene_menu_triggered,
        )

        self.model_selector_btn.setText(f"模型: {self.model_panel.model_combo.currentText()}")
        self.scene_selector_btn.setText(f"场景: {self.model_panel.mode_combo.currentText()}")
        self.model_selector_btn.setToolTip("切换当前模型")
        self.scene_selector_btn.setToolTip("切换 3D 场景模式")
        self.model_selector_btn.setMinimumWidth(self.model_selector_btn.sizeHint().width() + 6)
        self.scene_selector_btn.setMinimumWidth(self.scene_selector_btn.sizeHint().width() + 6)
        self._update_3d_status_summary()

    def _rebuild_combo_menu(self, menu: QtWidgets.QMenu, combo: QtWidgets.QComboBox, slot):
        menu.clear()
        action_group = QtWidgets.QActionGroup(menu)
        action_group.setExclusive(True)
        for index in range(combo.count()):
            action = menu.addAction(combo.itemText(index))
            action.setCheckable(True)
            action.setData(combo.itemData(index))
            action.setChecked(index == combo.currentIndex())
            action_group.addAction(action)
        action_group.triggered.connect(slot)
        return action_group

    def _on_model_menu_triggered(self, action: QtWidgets.QAction):
        index = self.model_panel.model_combo.findData(action.data())
        if index >= 0:
            self.model_panel.model_combo.setCurrentIndex(index)

    def _on_scene_menu_triggered(self, action: QtWidgets.QAction):
        index = self.model_panel.mode_combo.findData(action.data())
        if index >= 0:
            self.model_panel.mode_combo.setCurrentIndex(index)

    def _update_3d_status_summary(self):
        if hasattr(self, "model_summary_label"):
            self.model_summary_label.setText(self.model_panel.get_status_summary())

    def _sync_toolbar_state(self):
        self.connect_serial_action.setEnabled(self.serial_panel.connect_btn.isEnabled())
        self.disconnect_serial_action.setEnabled(self.serial_panel.disconnect_btn.isEnabled())
        self.run_action.setEnabled(not self._simulation_running)
        self.stop_action.setEnabled(self._simulation_running)
        self.command_panel.run_btn.setEnabled(not self._simulation_running)
        self.command_panel.stop_btn.setEnabled(self._simulation_running)
        self.record_action.setText("停止录制" if self.recorder.active else "开始录制")

    def _algo_id_from_name(self, algo_name: str) -> int:
        mapping = {
            "PID": 0,
            "LADRC": 1,
            "OPEN_LOOP": 2,
        }
        return mapping.get((algo_name or "").strip().upper(), 0)

    def _refresh_control_status(self):
        algo_name = ALGO_NAME.get(self._latest_telemetry.algo_id, f"ALG_{self._latest_telemetry.algo_id}")
        self.status_panel.update_control(
            algo_name,
            self._latest_telemetry.run_state,
            self._latest_telemetry.ref,
            self._latest_telemetry.feedback,
            self._latest_telemetry.u_cmd,
        )

    def _sync_local_control_cache(self):
        self._latest_telemetry.algo_id = self._algo_id_from_name(self.command_panel.algo_combo.currentData() or "PID")
        self._latest_telemetry.ref = float(self.command_panel.ref_spin.value())
        self._latest_telemetry.run_state = 1 if self._simulation_running else 0
        self._refresh_control_status()

    def _set_simulation_running(self, running: bool):
        running = bool(running)
        self._simulation_running = running
        self._latest_telemetry.run_state = 1 if running else 0
        self._last_sim_time = time.monotonic()
        if running:
            self.sim_timer.start()
        else:
            self.sim_timer.stop()
            self._reset_simulated_upload_state()
        self._refresh_control_status()
        self._sync_toolbar_state()
        self.statusBar().showMessage("仿真已启动" if running else "仿真已停止", 2500)

    def _apply_local_command_side_effects(self, command: str):
        normalized = " ".join(str(command).strip().upper().split())
        if not normalized:
            return
        if normalized == "RUN 1":
            self._set_simulation_running(True)
            return
        if normalized == "RUN 0":
            self._set_simulation_running(False)
            return
        if normalized.startswith("ALG "):
            algo_name = normalized[4:]
            self._latest_telemetry.algo_id = self._algo_id_from_name(algo_name)
            combo_index = self.command_panel.algo_combo.findData(algo_name)
            if combo_index >= 0:
                blocker = QtCore.QSignalBlocker(self.command_panel.algo_combo)
                self.command_panel.algo_combo.setCurrentIndex(combo_index)
                del blocker
            self._refresh_control_status()
            return
        if normalized.startswith("SET REF "):
            try:
                ref_value = float(normalized.split()[-1])
            except (TypeError, ValueError):
                return
            blocker = QtCore.QSignalBlocker(self.command_panel.ref_spin)
            self.command_panel.ref_spin.setValue(ref_value)
            del blocker
            self._latest_telemetry.ref = ref_value
            self._refresh_control_status()
            return
        if normalized == "GET STATUS" and self._is_simulated_upload_active():
            self._emit_simulated_status_snapshot()

    def _on_algorithm_selected(self, algo_name: str):
        self._latest_telemetry.algo_id = self._algo_id_from_name(algo_name)
        self._refresh_control_status()

    def _on_reference_changed(self, value: float):
        self._latest_telemetry.ref = float(value)
        self._refresh_control_status()

    def _apply_sim_period_ms(self, period_ms: int, show_message: bool = True):
        period_ms = max(1, int(period_ms))
        self._sim_period_ms = period_ms
        if hasattr(self, "sim_timer") and self.sim_timer is not None:
            self.sim_timer.setInterval(period_ms)
        self.cfg.sim_hz = max(1, int(round(1000.0 / period_ms)))
        if show_message:
            self.statusBar().showMessage(
                f"上位机运行周期已设置为 {period_ms} ms（约 {1000.0 / period_ms:.1f} Hz）",
                2500,
            )

    def _on_sim_period_changed(self, period_ms: int):
        self._apply_sim_period_ms(period_ms, show_message=True)

    def _on_disturbance_level_changed(self, level_key: str, scale: float):
        self._disturbance_level_key = level_key
        self._disturbance_scale = float(scale)
        for simulator in self._simulators.values():
            simulator.set_disturbance_scale(self._disturbance_scale)
        self.status_panel.set_disturbance_level(DISTURBANCE_LEVEL_TEXT.get(level_key, self.command_panel.current_disturbance_label()))
        self.statusBar().showMessage(
            f"环境扰动等级已切换为 {DISTURBANCE_LEVEL_TEXT.get(level_key, self.command_panel.current_disturbance_label())}",
            2500,
        )

    def _connect_selected_port(self):
        self.open_serial_signal.emit(self.serial_panel.port_combo.currentText(), int(self.serial_panel.baud_combo.currentText()))

    def _is_serial_connected(self) -> bool:
        return bool(self.serial_panel.disconnect_btn.isEnabled())

    @staticmethod
    def _format_console_float(value: float, decimals: int = 3) -> str:
        try:
            return f"{float(value):.{decimals}f}"
        except (TypeError, ValueError):
            return "0.000"

    def _format_telemetry_console_line(self, telemetry: Telemetry) -> str:
        parts = [
            f"timestamp={int(telemetry.timestamp_ms)}",
            f"roll={self._format_console_float(telemetry.roll, 2)}",
            f"pitch={self._format_console_float(telemetry.pitch, 2)}",
            f"yaw={self._format_console_float(telemetry.yaw, 2)}",
            f"u_cmd={self._format_console_float(telemetry.u_cmd, 3)}",
            f"ref={self._format_console_float(telemetry.ref, 3)}",
            f"feedback={self._format_console_float(telemetry.feedback, 3)}",
            f"algo={ALGO_NAME.get(int(telemetry.algo_id), f'ALG_{telemetry.algo_id}')}",
            f"run_state={int(telemetry.run_state)}",
        ]
        if getattr(telemetry, "extra", None):
            for key in sorted(telemetry.extra.keys()):
                parts.append(f"{key}={self._format_console_float(telemetry.extra[key], 3)}")
        return ",".join(parts)

    def _format_feedback_console_line(self, feedback: SimFeedback) -> str:
        return (
            f"timestamp={int(feedback.timestamp_ms)},"
            f"depth={self._format_console_float(feedback.depth, 5)},"
            f"depth_rate={self._format_console_float(feedback.depth_rate, 5)},"
            f"disturbance={self._format_console_float(feedback.disturbance, 5)}"
        )

    def _log_outbound_command(self, command: str):
        prefix = "[上位机->下位机][命令]" if self._is_serial_connected() else "[上位机命令][未连接]"
        self.log_panel.append_line(f"{prefix} {command}")

    def _log_outbound_feedback(self, feedback: SimFeedback):
        if not self._is_serial_connected():
            return
        mode = "二进制" if self.serial_panel.binary_cb.isChecked() else "文本"
        self.log_panel.append_line(
            f"[上位机->下位机][仿真反馈/{mode}] {self._format_feedback_console_line(feedback)}"
        )

    def _log_inbound_telemetry(self, telemetry: Telemetry):
        self.log_panel.append_line(f"[下位机->上位机][遥测] {self._format_telemetry_console_line(telemetry)}")

    def _log_simulated_inbound_telemetry(self, telemetry: Telemetry):
        self.log_panel.append_line(f"[模拟下位机->上位机][遥测] {self._format_telemetry_console_line(telemetry)}")

    def _send_toolbar_command(self, command: str):
        self._apply_local_command_side_effects(command)
        self._log_outbound_command(command)
        self.send_line_signal.emit(command)

    def _current_model_type(self) -> str:
        return self.model_panel.current_model_type()

    def _current_feedback(self) -> SimFeedback:
        return self._feedback_by_model[self._current_model_type()]

    def _normalize_feedback(self, model_type: str, feedback: SimFeedback) -> SimFeedback:
        if model_type != "aircraft":
            return feedback

        clamped_height = max(0.0, float(feedback.depth))
        vertical_rate = float(feedback.depth_rate)
        if clamped_height <= 1e-6 and vertical_rate < 0.0:
            vertical_rate = 0.0
        return SimFeedback(
            timestamp_ms=feedback.timestamp_ms,
            depth=clamped_height,
            depth_rate=vertical_rate,
            disturbance=feedback.disturbance,
        )

    def _refresh_ports(self):
        ports = SerialWorker.list_ports()
        self.serial_panel.set_ports(ports)

    def _send_command(self, command: str):
        self._apply_local_command_side_effects(command)
        self._log_outbound_command(command)
        self.send_line_signal.emit(command)

    def _send_preset_command(self, command: str):
        self._apply_local_command_side_effects(command)
        self._log_outbound_command(command)
        self.send_line_signal.emit(command)

    def _set_record_path_text(self, text: str):
        metrics = self.record_path_label.fontMetrics()
        elided = metrics.elidedText(text, QtCore.Qt.ElideMiddle, 300)
        self.record_path_label.setText(elided)
        self.record_path_label.setToolTip(text)

    def _toggle_record(self):
        if self.recorder.active:
            self.recorder.stop()
            self.record_btn.setText("开始录制")
            self._set_record_path_text("录制已停止")
            self.statusBar().showMessage("CSV 录制已停止", 3000)
            self._sync_toolbar_state()
            return

        default_name = f"log_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        target, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "保存 CSV",
            str(Path.cwd() / default_name),
            "CSV 文件 (*.csv)",
        )
        if not target:
            return

        self.recorder.start(Path(target))
        self.record_btn.setText("停止录制")
        self._set_record_path_text(target)
        self.log_panel.append_line(f"[录制] 开始 -> {target}")
        self.statusBar().showMessage("CSV 录制已开始", 3000)
        self._sync_toolbar_state()

    def _on_connection_changed(self, connected: bool, desc: str):
        if not connected:
            self._legacy_binary_feedback_warned = False
        self.serial_panel.set_connected(connected, desc)
        self._sync_toolbar_state()
        state = "已连接" if connected else "已断开"
        suffix = f" {desc}" if desc else ""
        self.log_panel.append_line(f"[串口] {state}{suffix}")
        if self._simulate_device_upload:
            if connected:
                self.log_panel.append_line("[模拟下位机] 已检测到真实串口连接，模拟上报已自动暂停。")
            else:
                self.log_panel.append_line("[模拟下位机] 当前未连接串口，可使用本地模拟上报体验软件。")
        self.statusBar().showMessage(f"串口状态: {state}{suffix}", 3000)

    def _on_line(self, line: str):
        self.log_panel.append_line(f"[下位机->上位机][文本] {line}")

    def _append_log_error(self, text: str):
        self.log_panel.append_line(f"[错误] {text}")
        self.statusBar().showMessage(f"错误: {text}", 5000)

    def _on_stats(self, stats: dict):
        self._last_rx_ms = int(stats.get("last_rx_ms", 0))
        self._last_stats = {
            "rx_frames": int(stats.get("rx_frames", 0)),
            "tx_frames": int(stats.get("tx_frames", 0)),
            "parse_errors": int(stats.get("parse_errors", 0)),
            "latency_ms": int(stats.get("last_latency_ms", 0)),
        }
        self.status_panel.update_comm(**self._last_stats)

    def _on_model_context_changed(self):
        model_type = self._current_model_type()
        current_feedback = self._feedback_by_model[model_type]
        self._latest_feedback = current_feedback
        self._reset_simulated_upload_state()
        self.status_panel.set_model_context(model_type)
        self.status_panel.set_disturbance_level(
            DISTURBANCE_LEVEL_TEXT.get(self._disturbance_level_key, self.command_panel.current_disturbance_label())
        )
        self.status_panel.update_vertical_state(
            current_feedback.depth,
            current_feedback.depth_rate,
            current_feedback.disturbance,
        )
        self.plot_panel.set_model_context(model_type)
        self.plot_panel.clear_model_series()
        self.model_panel.update_depth(current_feedback.depth)
        self._update_3d_status_summary()
        self._sync_wave_actions()
        self._schedule_navigation_refresh()
        self.statusBar().showMessage(f"已切换到 {MODEL_NAME.get(model_type, model_type)}", 2500)

    def _apply_telemetry(self, telemetry: Telemetry, simulated: bool = False):
        previous_feedback = self._latest_telemetry.feedback
        feedback_missing = bool(getattr(telemetry, "extra", {}).pop("_feedback_missing", 0.0))
        if feedback_missing:
            telemetry.feedback = self._current_feedback().depth if self._simulation_running else previous_feedback
            if not self._legacy_binary_feedback_warned:
                self.log_panel.append_line(
                    "[协议] 当前二进制遥测未包含 feedback，界面暂使用上一反馈值/仿真反馈值。建议升级为文本遥测或扩展二进制遥测。"
                )
                self._legacy_binary_feedback_warned = True
        self._latest_telemetry = telemetry
        if simulated:
            self._simulated_upload_rx_frames += 1
            self._last_rx_ms = int(time.time() * 1000)
            self.status_panel.update_comm(self._simulated_upload_rx_frames, 0, 0, 0)
            self.status_panel.set_timeout(False)
            self._log_simulated_inbound_telemetry(telemetry)
        else:
            self._log_inbound_telemetry(telemetry)

        now_s = time.monotonic() - self._start_monotonic
        algo_name = ALGO_NAME.get(telemetry.algo_id, f"ALG_{telemetry.algo_id}")
        self.status_panel.update_control(
            algo_name,
            telemetry.run_state,
            telemetry.ref,
            telemetry.feedback,
            telemetry.u_cmd,
        )
        self.plot_panel.append(
            now_s,
            {
                "ref": telemetry.ref,
                "feedback": telemetry.feedback,
                "u_cmd": telemetry.u_cmd,
                "roll": telemetry.roll,
                "pitch": telemetry.pitch,
                "yaw": telemetry.yaw,
            },
        )

        current_feedback = self._current_feedback()
        self.model_panel.update_pose(
            telemetry.roll,
            telemetry.pitch,
            telemetry.yaw,
            current_feedback.depth,
            telemetry.u_cmd,
        )

    def _on_telemetry(self, telemetry: Telemetry):
        self._apply_telemetry(telemetry, simulated=False)

    def _reset_simulated_upload_state(self):
        self._simulated_upload_integral = 0.0
        self._simulated_upload_yaw = 0.0
        self._simulated_upload_rx_frames = 0

    def _is_simulated_upload_active(self) -> bool:
        return bool(self._simulate_device_upload and not self._is_serial_connected())

    def _on_simulated_upload_changed(self, enabled: bool):
        enabled = bool(enabled)
        previous = self._simulate_device_upload
        self._simulate_device_upload = enabled
        if previous == enabled:
            return
        self._reset_simulated_upload_state()
        if self._simulate_device_upload:
            self.log_panel.append_line("[模拟下位机] 已启用模拟上报模式，未连接串口时将本地生成遥测。")
            self.statusBar().showMessage("已启用模拟下位机上传模式，可在不连接串口时体验软件。", 3500)
        else:
            if not self._is_serial_connected():
                self._last_rx_ms = 0
                self.status_panel.update_comm(0, 0, 0, 0)
                self.status_panel.set_timeout(False)
            self.log_panel.append_line("[模拟下位机] 已关闭模拟上报模式。")
            self.statusBar().showMessage("已关闭模拟下位机上传模式。", 2500)

    def _simulated_control_gains(self, model_type: str, algo_name: str):
        pid_gains = {
            "rov": (1.15, 0.14, 0.62),
            "aircraft": (1.45, 0.10, 0.78),
            "generic": (1.05, 0.12, 0.50),
        }
        ladrc_gains = {
            "rov": (1.35, 0.65, 0.18),
            "aircraft": (1.55, 0.82, 0.12),
            "generic": (1.20, 0.58, 0.15),
        }
        if algo_name == "LADRC":
            return ladrc_gains.get(model_type, ladrc_gains["rov"])
        return pid_gains.get(model_type, pid_gains["rov"])

    def _generate_simulated_pose(self, model_type: str, u_cmd: float, feedback: SimFeedback, now_s: float, dt: float):
        yaw_bias = {"rov": 4.0, "aircraft": 10.0, "generic": 6.0}.get(model_type, 4.0)
        yaw_gain = {"rov": 12.0, "aircraft": 24.0, "generic": 16.0}.get(model_type, 12.0)
        self._simulated_upload_yaw = (self._simulated_upload_yaw + (yaw_bias + yaw_gain * u_cmd) * dt) % 360.0

        if model_type == "aircraft":
            roll = max(-28.0, min(28.0, math.sin(now_s * 0.92) * 6.0 + u_cmd * 5.5))
            pitch = max(-20.0, min(20.0, math.cos(now_s * 0.66) * 4.0 + feedback.depth_rate * 42.0))
        elif model_type == "generic":
            roll = max(-16.0, min(16.0, math.sin(now_s * 0.75) * 4.0 + u_cmd * 3.2))
            pitch = max(-12.0, min(12.0, math.cos(now_s * 0.58) * 3.0 + feedback.depth_rate * 28.0))
        else:
            roll = max(-12.0, min(12.0, math.sin(now_s * 0.70) * 3.0 + u_cmd * 2.4))
            pitch = max(-10.0, min(10.0, math.cos(now_s * 0.54) * 2.8 + feedback.depth_rate * 22.0))
        return roll, pitch, self._simulated_upload_yaw

    def _generate_simulated_upload_telemetry(self, dt: float) -> Telemetry:
        model_type = self._current_model_type()
        feedback = self._current_feedback()
        now_s = time.monotonic() - self._start_monotonic
        now_ms = int(time.time() * 1000)
        algo_name = str(self.command_panel.algo_combo.currentData() or "PID").strip().upper()
        ref = float(self.command_panel.ref_spin.value())
        error = ref - float(feedback.depth)

        if algo_name == "OPEN_LOOP":
            u_cmd = max(-3.0, min(3.0, ref if abs(ref) > 1e-6 else math.sin(now_s * 0.65) * 1.2))
        else:
            g1, g2, g3 = self._simulated_control_gains(model_type, algo_name)
            self._simulated_upload_integral += error * dt
            self._simulated_upload_integral = max(-6.0, min(6.0, self._simulated_upload_integral))
            if algo_name == "LADRC":
                u_cmd = g1 * error - g2 * float(feedback.depth_rate) - g3 * float(feedback.disturbance)
            else:
                u_cmd = g1 * error + g3 * self._simulated_upload_integral - g2 * float(feedback.depth_rate)
            u_cmd = max(-3.0, min(3.0, u_cmd))

        roll, pitch, yaw = self._generate_simulated_pose(model_type, u_cmd, feedback, now_s, dt)
        return Telemetry(
            timestamp_ms=now_ms,
            roll=roll,
            pitch=pitch,
            yaw=yaw,
            u_cmd=u_cmd,
            ref=ref,
            feedback=float(feedback.depth),
            algo_id=self._algo_id_from_name(algo_name),
            run_state=1 if self._simulation_running else 0,
        )

    def _emit_simulated_status_snapshot(self):
        telemetry = self._generate_simulated_upload_telemetry(max(1e-3, self._sim_period_ms / 1000.0))
        telemetry.run_state = 1 if self._simulation_running else 0
        self._apply_telemetry(telemetry, simulated=True)

    def _on_sim_tick(self):
        if not self._simulation_running:
            return
        now = time.monotonic()
        dt = max(1e-4, now - self._last_sim_time)
        self._last_sim_time = now

        model_type = self._current_model_type()
        if self._is_simulated_upload_active():
            telemetry = self._generate_simulated_upload_telemetry(dt)
            self._apply_telemetry(telemetry, simulated=True)
        raw_feedback = self._simulators[model_type].step(dt, self._latest_telemetry.u_cmd)
        feedback = self._normalize_feedback(model_type, raw_feedback)
        self._feedback_by_model[model_type] = feedback
        self._latest_feedback = feedback

        now_s = time.monotonic() - self._start_monotonic
        self.plot_panel.append(
            now_s,
            {
                "vertical": feedback.depth,
                "vertical_rate": feedback.depth_rate,
                "disturbance": feedback.disturbance,
            },
        )
        self.status_panel.update_vertical_state(
            feedback.depth,
            feedback.depth_rate,
            feedback.disturbance,
        )
        self.model_panel.update_depth(feedback.depth)

        tx_period = 1.0 / max(1, self.cfg.serial_tx_hz)
        if now - self._last_serial_tx >= tx_period:
            self._log_outbound_feedback(feedback)
            self.send_feedback_signal.emit(feedback)
            self._last_serial_tx = now

        if self.recorder.active:
            row = telemetry_to_record_dict(self._latest_telemetry)
            row.update(
                {
                    "pc_time_ms": int(time.time() * 1000),
                    "sim_model": model_type,
                    "sim_vertical": feedback.depth,
                    "sim_vertical_rate": feedback.depth_rate,
                    "sim_disturbance": feedback.disturbance,
                    "sim_disturbance_level": self._disturbance_level_key,
                    "sim_disturbance_scale": self._disturbance_scale,
                }
            )
            self.recorder.write_row(row)

    def _update_timeout_state(self):
        if self._last_rx_ms <= 0:
            self.status_panel.set_timeout(False)
            return
        timeout = (int(time.time() * 1000) - self._last_rx_ms) > self.cfg.communication_timeout_ms
        self.status_panel.set_timeout(timeout)


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(DEFAULT_CONFIG.app_name)
    app.setApplicationDisplayName(DEFAULT_CONFIG.app_name)
    app.setApplicationVersion(DEFAULT_CONFIG.app_version)
    app.setOrganizationName(DEFAULT_CONFIG.app_author)
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "embedded.newstart.control-algorithm-simulator"
            )
        except Exception:
            pass
    if APP_ICON_PATH.exists():
        icon = QtGui.QIcon(str(APP_ICON_PATH))
        if not icon.isNull():
            app.setWindowIcon(icon)
    splash = StartupSplash(DEFAULT_CONFIG)
    splash.show_centered()
    splash.set_stage_info("正在加载主界面", "正在准备窗口资源与启动动画", 18)
    app.processEvents()

    splash.set_stage_info("正在初始化控制工作台", "正在构建设备、控制、通道与波形页面", 42)
    win = MainWindow()
    splash.set_stage_info("正在恢复主题与工作台", "正在应用海洋蓝调主题与上次布局设置", 78)
    app.processEvents()

    QtCore.QTimer.singleShot(160, lambda: splash.finish_with(win))
    QtCore.QTimer.singleShot(620, win._show_welcome_page)
    return app.exec_()
