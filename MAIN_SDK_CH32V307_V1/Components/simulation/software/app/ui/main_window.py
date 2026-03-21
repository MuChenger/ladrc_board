import json
import sys
import time
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
USER_SETTINGS_PATH = SOFTWARE_ROOT / "user_settings.json"
DISTURBANCE_LEVEL_TEXT = {
    "off": "关闭",
    "low": "低",
    "medium": "中",
    "high": "高",
    "extreme": "极高",
}


class MainWindow(QtWidgets.QMainWindow):
    send_line_signal = QtCore.pyqtSignal(str)
    send_feedback_signal = QtCore.pyqtSignal(object)
    open_serial_signal = QtCore.pyqtSignal(str, int)
    close_serial_signal = QtCore.pyqtSignal()
    set_binary_signal = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.cfg = DEFAULT_CONFIG
        self.setWindowTitle(self.cfg.app_name)
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

        self.recorder = CsvRecorder()

        self._build_ui()
        self._apply_workbench_style()
        self._setup_worker()
        self._setup_timers()
        self._refresh_ports()
        self._on_model_context_changed()
        self._capture_default_layout()
        self._load_persistent_settings()

    def closeEvent(self, event):
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
            "rov": DepthPlantSimulator(),
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

        central_host = QtWidgets.QWidget()
        central_layout = QtWidgets.QVBoxLayout(central_host)
        central_layout.setContentsMargins(8, 8, 8, 8)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.plot_panel)
        self.setCentralWidget(central_host)

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
        self.command_panel.console_message.connect(self.log_panel.append_line)
        self.command_panel.disturbance_level_changed.connect(self._on_disturbance_level_changed)
        self.preset_command_panel.send_command.connect(self._send_preset_command)
        self.record_btn.clicked.connect(self._toggle_record)
        self.model_panel.model_combo.currentIndexChanged.connect(self._on_model_context_changed)

        self._on_disturbance_level_changed(
            self.command_panel.current_disturbance_key(),
            self.command_panel.current_disturbance_scale(),
        )
        self._sync_navigation_state()
        self._sync_toolbar_state()

    def _build_workbench_docks(self):
        connection_view = self._make_connection_view()
        control_view = self._make_control_view()
        channel_view = self._wrap_scroll_area(self.channel_widget)

        self.connection_dock = self._create_dock("设备", connection_view, "dock_connection")
        self.control_dock = self._create_dock("控制", control_view, "dock_control")
        self.channel_dock = self._create_dock("通道", channel_view, "dock_channels")
        self.model_dock = self._create_dock("3D 视图", self.model_panel, "dock_model")
        self.status_dock = self._create_dock("运行状态", self.status_panel, "dock_status")
        self.log_dock = self._create_dock("控制台", self.log_panel, "dock_console")

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

        self.resizeDocks([self.connection_dock, self.model_dock], [450, 320], QtCore.Qt.Horizontal)
        self.resizeDocks([self.log_dock], [210], QtCore.Qt.Vertical)

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

    def _wrap_scroll_area(self, widget: QtWidgets.QWidget):
        area = QtWidgets.QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QtWidgets.QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        area.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        area.setAlignment(QtCore.Qt.AlignTop)
        widget.setMinimumWidth(0)
        area.setWidget(widget)
        return area

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

        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)

        self.file_menu = menu_bar.addMenu("文件")
        self.file_menu.addAction(self.record_action)
        self.file_menu.addSeparator()
        self.exit_action = self.file_menu.addAction("退出")
        self.exit_action.triggered.connect(self.close)

        self.settings_menu = menu_bar.addMenu("设置")
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
        self.workbench_toolbar.addAction(self.follow_view_action)
        self.workbench_toolbar.addAction(self.model_panel.reset_view_action)
        self.workbench_toolbar.addAction(self.model_panel.clear_trail_action)
        self.workbench_toolbar.addSeparator()
        self.workbench_toolbar.addWidget(self.model_panel.action_menu_btn)

        self.statusBar().showMessage("Eclipse 风格工作台布局已加载")
        self.model_summary_label = QtWidgets.QLabel()
        self.model_summary_label.setStyleSheet("padding: 0 6px; color: #586b7d;")
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

        self._rebuild_wave_measure_channel_menu()

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

    def _apply_workbench_style(self):
        font = QtGui.QFont("Microsoft YaHei UI", 9)
        self.setFont(font)
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #f3f5f7; color: #1d2e3f; }
            QMenuBar { background: #eceff3; border-bottom: 1px solid #cfd7df; }
            QMenuBar::item { padding: 5px 10px; background: transparent; }
            QMenuBar::item:selected { background: #dfe6ee; }
            QMenu { background: #ffffff; border: 1px solid #c9d1da; padding: 4px; }
            QMenu::item { padding: 6px 18px; }
            QMenu::item:selected { background: #dfe9f4; }
            QToolBar { background: #eceff3; border-bottom: 1px solid #cfd7df; spacing: 4px; padding: 4px 6px; }
            QToolBar::separator { background: #c3ccd6; width: 1px; margin: 4px 6px; }
            QPushButton, QToolButton {
                background: #ffffff; border: 1px solid #bec8d2; border-radius: 4px; padding: 5px 10px; color: #1d2e3f;
            }
            QPushButton:hover, QToolButton:hover { background: #f0f4f8; border-color: #97abc1; }
            QPushButton:pressed, QToolButton:pressed { background: #e3ebf3; }
            QPushButton:disabled, QToolButton:disabled { color: #8a98a7; background: #f5f7f9; border-color: #d4dbe2; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
                background: #ffffff; border: 1px solid #c3ccd6; border-radius: 4px; padding: 5px 7px; selection-background-color: #2d70b3;
            }
            QComboBox::drop-down { border: none; width: 22px; }
            QGroupBox {
                background: #ffffff; border: 1px solid #ccd5de; border-radius: 6px; margin-top: 10px; font-weight: 600; padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #2a3d53; }
            QDockWidget::title {
                background: #e7ebf0; border: 1px solid #ccd5de; border-bottom: none; padding: 6px 10px; text-align: left; color: #26415c;
            }
            QMainWindow::separator { background: #c8d0d8; width: 4px; height: 4px; }
            QScrollArea { border: none; background: #f3f5f7; }
            QStatusBar { background: #eceff3; border-top: 1px solid #cfd7df; }
            QLabel[statusKey="true"] { color: #61758a; }
            QLabel[statusValue="true"] { color: #12314c; font-weight: 600; }
            QLabel#statusHint { color: #667b90; }
            QLabel#sectionTitle { font-weight: 700; color: #22405d; }
            QFrame#recordCard { background: #ffffff; border: 1px solid #ccd5de; border-radius: 6px; }
            QFrame#presetRow { background: #f7f9fb; border: 1px solid #d7dee6; border-radius: 6px; }
            QPlainTextEdit#consoleView { background: #111827; color: #d7e2f0; border-color: #293548; border-radius: 6px; }
            """
        )

    def _capture_default_layout(self):
        self._default_window_geometry = self.saveGeometry()
        self._default_window_state = self.saveState()

    def _restore_default_layout(self):
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
            "version": 1,
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

        self.serial_panel.apply_state(payload.get("serial_panel", {}))
        self.command_panel.apply_state(payload.get("command_panel", {}))
        self.preset_command_panel.apply_state(payload.get("preset_panel", {}))
        self.plot_panel.apply_state(payload.get("plot_panel", {}))
        self.model_panel.apply_state(payload.get("model_panel", {}))

        window_state = payload.get("window", {})
        if isinstance(window_state, dict):
            geometry = self._deserialize_byte_array(str(window_state.get("geometry", "")))
            state = self._deserialize_byte_array(str(window_state.get("state", "")))
            if geometry is not None:
                self.restoreGeometry(geometry)
            if state is not None:
                self.restoreState(state)

        self._sync_wave_actions()
        self._sync_navigation_state()
        self._sync_toolbar_state()
        self._update_3d_status_summary()

    def _write_settings_file(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._collect_settings_payload(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_settings_file(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_persistent_settings(self):
        try:
            self._write_settings_file(USER_SETTINGS_PATH)
        except Exception:
            pass

    def _load_persistent_settings(self):
        if not USER_SETTINGS_PATH.exists():
            return
        try:
            self._apply_settings_payload(self._read_settings_file(USER_SETTINGS_PATH))
        except Exception:
            self.statusBar().showMessage("已忽略损坏的本地设置文件", 3000)

    def _export_settings_via_dialog(self):
        default_name = f"ui_settings_{time.strftime('%Y%m%d_%H%M%S')}.json"
        target, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出设置",
            str(SOFTWARE_ROOT / default_name),
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
            str(SOFTWARE_ROOT),
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
        self.serial_panel.reset_to_defaults()
        self.command_panel.reset_to_defaults()
        self.preset_command_panel.reset_to_defaults()
        self.plot_panel.reset_to_defaults()
        self.model_panel.reset_to_defaults()
        if self._default_window_geometry is not None:
            self.restoreGeometry(self._default_window_geometry)
        self._restore_default_layout()
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
        self.sim_timer.setInterval(int(1000 / self.cfg.sim_hz))
        self.sim_timer.timeout.connect(self._on_sim_tick)
        self.sim_timer.start()

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
        self.record_action.setText("停止录制" if self.recorder.active else "开始录制")

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

    def _send_toolbar_command(self, command: str):
        self.send_line_signal.emit(command)
        self.log_panel.append_line(f"> {command}")

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
        self.send_line_signal.emit(command)

    def _send_preset_command(self, command: str):
        self.send_line_signal.emit(command)
        self.log_panel.append_line(f"> {command}")

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
        self.serial_panel.set_connected(connected, desc)
        self._sync_toolbar_state()
        state = "已连接" if connected else "已断开"
        suffix = f" {desc}" if desc else ""
        self.log_panel.append_line(f"[串口] {state}{suffix}")
        self.statusBar().showMessage(f"串口状态: {state}{suffix}", 3000)

    def _on_line(self, line: str):
        self.log_panel.append_line(line)

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

    def _on_telemetry(self, telemetry: Telemetry):
        self._latest_telemetry = telemetry

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

    def _on_sim_tick(self):
        now = time.monotonic()
        dt = max(1e-4, now - self._last_sim_time)
        self._last_sim_time = now

        model_type = self._current_model_type()
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
    win = MainWindow()
    win.show()
    return app.exec_()
