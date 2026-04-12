import csv
import math
from bisect import bisect_left
from collections import deque
from pathlib import Path
from typing import Dict, List, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg


class PlotPanel(QtWidgets.QWidget):
    channel_toggled = QtCore.pyqtSignal(str, bool)
    DISTURBANCE_CHANNELS = {"disturbance_sim"}
    ALGORITHM_CHANNELS = {"u_cmd", "v1", "v2", "z1", "z2", "z3", "disturbance_remote"}
    LADRC_ONLY_CHANNELS = {"v1", "v2", "z1", "z2", "z3"}
    COMMON_CHANNELS = {"ref", "feedback", "roll", "pitch", "yaw", "vertical", "vertical_rate", "disturbance_sim"}
    DISPLAY_SMOOTHING_EXCLUDED = {"ref"}
    DISPLAY_SMOOTHING_WEIGHTS = (1.0, 2.0, 3.0, 2.0, 1.0)
    DEFAULT_VISIBLE_CHANNELS = {"ref", "feedback"}
    BALANCE_RUNTIME_CHANNELS = {"u_cmd", "v1", "v2", "z1", "z2", "z3"}
    DEFAULT_CHANNEL_ORDER = ["ref", "feedback", "disturbance_sim", "roll", "pitch", "yaw"]
    LOCAL_CHANNEL_ORDER = []
    REMOTE_FIXED_CHANNEL_ORDER = ["u_cmd", "v1", "v2", "z1", "z2", "z3"]
    REMOTE_FIXED_CHANNELS_BY_ALGO = {
        "LADRC": ["u_cmd", "v1", "v2", "z1", "z2", "z3", "disturbance_remote"],
        "PID": ["u_cmd", "disturbance_remote"],
        "OPEN_LOOP": ["u_cmd", "disturbance_remote"],
    }
    STATIC_SECTION_TITLES = {
        "default": "默认通道",
        "local": "运行扩展",
        "remote": "下位机上传",
    }
    CHANNEL_DISPLAY_ORDER = [
        "ref",
        "feedback",
        "disturbance_sim",
        "u_cmd",
        "v1",
        "v2",
        "z1",
        "z2",
        "z3",
        "roll",
        "pitch",
        "yaw",
    ]
    DYNAMIC_GROUP_ORDER = ("output", "state", "error")
    DYNAMIC_GROUP_TITLES = {
        "output": "算法输出",
        "state": "算法状态",
        "error": "算法误差",
    }
    DYNAMIC_CHANNEL_COLORS = (
        "#f59e0b",
        "#8b5cf6",
        "#14b8a6",
        "#ec4899",
        "#22c55e",
        "#0ea5e9",
        "#f43f5e",
        "#a855f7",
        "#84cc16",
        "#06b6d4",
    )

    CHANNEL_LABELS = {
        "ref": "期望值",
        "feedback": "仿真值",
        "u_cmd": "控制输出",
        "pid_error": "PID 误差",
        "pid_integral": "PID 积分累积",
        "pid_rate": "PID 微分输入",
        "pid_p_out": "比例项 P",
        "pid_i_out": "积分项 I",
        "pid_d_out": "微分项 D",
        "pid_u_raw": "未限幅输出",
        "v1": "TD 输出 v1",
        "v2": "TD 输出 v2",
        "z1": "ESO 状态 z1",
        "z2": "ESO 状态 z2",
        "z3": "ESO 状态 z3",
        "sim_mode": "LADRC 模式",
        "r": "跟踪带宽 r",
        "h": "采样周期 h",
        "w0": "观测器带宽 w0",
        "wc": "控制器带宽 wc",
        "b0": "估计增益 b0",
        "init": "初始值 init",
        "roll": "姿态角-滚转",
        "pitch": "姿态角-俯仰",
        "yaw": "姿态角-偏航",
        "vertical": "垂向量",
        "vertical_rate": "垂向速度",
        "disturbance_sim": "环境扰动",
        "disturbance_remote": "算法扰动",
    }
    MODEL_VERTICAL_LABELS = {
        "rov": ("仿真深度", "深度变化率", "环境扰动"),
        "aircraft": ("仿真高度", "高度变化率", "气流扰动"),
        "generic": ("垂向位置", "垂向速度", "外部扰动"),
    }
    PRESET_CHANNELS = {
        "balance": {
            "ref": True,
            "feedback": True,
            "u_cmd": False,
            "v1": False,
            "v2": False,
            "z1": False,
            "z2": False,
            "z3": False,
            "roll": False,
            "pitch": False,
            "yaw": False,
            "disturbance_sim": False,
        },
        "attitude": {
            "ref": False,
            "feedback": False,
            "u_cmd": False,
            "v1": False,
            "v2": False,
            "z1": False,
            "z2": False,
            "z3": False,
            "roll": True,
            "pitch": True,
            "yaw": True,
            "disturbance_sim": False,
        },
        "vertical": {
            "ref": True,
            "feedback": True,
            "u_cmd": True,
            "v1": False,
            "v2": False,
            "z1": False,
            "z2": False,
            "z3": False,
            "roll": False,
            "pitch": False,
            "yaw": False,
            "disturbance_sim": False,
        },
        "pid": {
            "ref": True,
            "feedback": True,
            "u_cmd": True,
            "pid_error": True,
            "pid_p_out": True,
            "pid_i_out": True,
            "pid_d_out": True,
            "pid_integral": False,
            "pid_rate": False,
            "pid_u_raw": False,
            "roll": False,
            "pitch": False,
            "yaw": False,
            "disturbance_sim": False,
            "disturbance_remote": False,
        },
        "ladrc": {
            "ref": True,
            "feedback": True,
            "u_cmd": True,
            "v1": True,
            "v2": True,
            "z1": True,
            "z2": True,
            "z3": True,
            "roll": False,
            "pitch": False,
            "yaw": False,
            "disturbance_sim": False,
        },
        "all": {
            "ref": True,
            "feedback": True,
            "u_cmd": True,
            "v1": True,
            "v2": True,
            "z1": True,
            "z2": True,
            "z3": True,
            "roll": True,
            "pitch": True,
            "yaw": True,
            "disturbance_sim": False,
        },
    }
    VIEWBOX_MENU_TEXTS = {
        "ViewBox options": "视图选项",
        "View All": "显示全部",
        "X axis": "X 轴",
        "Y axis": "Y 轴",
        "Mouse Mode": "鼠标模式",
        "3 button": "三键平移",
        "1 button": "框选缩放",
    }
    VIEWBOX_WIDGET_TEXTS = {
        "label": "关联坐标轴：",
        "autoRadio": "自动",
        "manualRadio": "手动",
        "invertCheck": "反转坐标轴",
        "mouseCheck": "启用鼠标交互",
        "visibleOnlyCheck": "仅可见数据",
        "autoPanCheck": "仅自动平移",
    }
    PLOT_MENU_TEXTS = {
        "Plot Options": "波形选项",
        "Transforms": "变换",
        "Downsample": "下采样",
        "Average": "平均",
        "Alpha": "透明度",
        "Grid": "网格",
        "Points": "数据点",
    }
    PLOT_WIDGET_TEXTS = {
        "logXCheck": "X 对数",
        "derivativeCheck": "导数 dy/dx",
        "phasemapCheck": "Y 与 Y'",
        "fftCheck": "功率谱 (FFT)",
        "logYCheck": "Y 对数",
        "subtractMeanCheck": "减去均值",
        "clipToViewCheck": "裁剪到视图",
        "maxTracesCheck": "最大轨迹数：",
        "downsampleCheck": "启用下采样",
        "forgetTracesCheck": "忽略隐藏轨迹",
        "peakRadio": "峰值",
        "meanRadio": "均值",
        "subsampleRadio": "抽样",
        "autoDownsampleCheck": "自动",
        "averageGroup": "平均",
        "alphaGroup": "透明度",
        "autoAlphaCheck": "自动",
        "xGridCheck": "显示 X 网格",
        "yGridCheck": "显示 Y 网格",
        "label": "透明度",
        "pointsGroup": "数据点",
        "autoPointsCheck": "自动",
    }
    SCENE_MENU_TEXTS = {
        "Export...": "导出...",
    }

    def __init__(self, window_sec: float = 20.0, parent=None):
        super().__init__(parent)
        self.window_sec = window_sec
        self.max_points = 4000
        self._paused = False
        self._channels: Dict[str, Dict[str, object]] = {}
        self._channel_widget_detached = False
        self._latest_time = 0.0
        self._updating_view = 0
        self._history_navigation = False
        self._view_history: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        self._view_history_index = -1
        self._last_mouse_x = 0.0
        self._point_markers = []
        self._theme = self._default_theme()
        self._algorithm_channel_labels: Dict[str, str] = {}
        self._dynamic_algorithm_channels: List[str] = []
        self._dynamic_channel_owners: Dict[str, str] = {}
        self._current_algorithm_key = "LADRC"
        self._channel_section_headers: List[QtWidgets.QLabel] = []
        self._runtime_channel_expanded = False
        self._build()
        self._init_channels()
        self._reflow_channel_layout()
        self._populate_measure_channel_combo()
        self._install_shortcuts()
        self.apply_preset(self.preset_combo.currentData())
        self._set_mouse_mode("pan")
        self._set_default_x_range()
        self._push_view_history(force=True)
        self.apply_theme(self._theme)

    @staticmethod
    def _default_theme() -> dict:
        return {
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
        }

    def _wrap_toolbar_row(self, widget: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
        widget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        scroll = QtWidgets.QScrollArea()
        scroll.setObjectName("toolbarRowScroll")
        scroll.setWidgetResizable(False)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setWidget(widget)
        height = max(widget.sizeHint().height() + 10, 44)
        scroll.setMinimumHeight(height)
        scroll.setMaximumHeight(height + 6)
        return scroll

    @staticmethod
    def _to_qcolor(value) -> QtGui.QColor:
        if isinstance(value, QtGui.QColor):
            return QtGui.QColor(value)
        if isinstance(value, (tuple, list)):
            parts = [int(v) for v in value]
            if len(parts) == 4:
                return QtGui.QColor(parts[0], parts[1], parts[2], parts[3])
            if len(parts) == 3:
                return QtGui.QColor(parts[0], parts[1], parts[2])
        text = str(value).strip()
        if text.startswith("rgba(") and text.endswith(")"):
            parts = [int(float(v.strip())) for v in text[5:-1].split(",")]
            if len(parts) == 4:
                return QtGui.QColor(parts[0], parts[1], parts[2], parts[3])
        if text.startswith("rgb(") and text.endswith(")"):
            parts = [int(float(v.strip())) for v in text[4:-1].split(",")]
            if len(parts) == 3:
                return QtGui.QColor(parts[0], parts[1], parts[2])
        color = QtGui.QColor(text)
        if color.isValid():
            return color
        return QtGui.QColor("#ffffff")

    def _build(self):
        self._root_layout = QtWidgets.QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(8)

        tool_widget = QtWidgets.QFrame()
        tool_widget.setObjectName("panelCard")
        tool_layout = QtWidgets.QVBoxLayout(tool_widget)
        tool_layout.setContentsMargins(12, 10, 12, 10)
        tool_layout.setSpacing(6)

        row1_widget = QtWidgets.QWidget()
        row1 = QtWidgets.QHBoxLayout(row1_widget)
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(8)
        self.pause_btn = QtWidgets.QPushButton("暂停")
        self.clear_btn = QtWidgets.QPushButton("清空")
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItem("平衡视图", "balance")
        self.preset_combo.addItem("姿态调试", "attitude")
        self.preset_combo.addItem("垂向控制", "vertical")
        self.preset_combo.addItem("PID 调试", "pid")
        self.preset_combo.addItem("LADRC 状态", "ladrc")
        self.preset_combo.addItem("全量监视", "all")
        self.preset_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.window_spin = QtWidgets.QDoubleSpinBox()
        self.window_spin.setRange(5.0, 120.0)
        self.window_spin.setValue(self.window_sec)
        self.window_spin.setSuffix(" s")
        self.window_spin.setSingleStep(5.0)
        self.follow_latest_cb = QtWidgets.QCheckBox("实时跟随")
        self.follow_latest_cb.setChecked(True)
        self.focus_btn = QtWidgets.QPushButton("一键聚焦")
        self.more_tools_btn = QtWidgets.QToolButton()
        self.more_tools_btn.setText("更多工具")
        self.more_tools_btn.setCheckable(True)
        self.more_tools_btn.setChecked(False)
        self.more_tools_btn.setProperty("secondaryRole", True)
        self.more_tools_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.annotation_cb = QtWidgets.QCheckBox("点击标记")
        self.readout_label = QtWidgets.QLabel("游标: --")
        self.readout_label.setObjectName("panelSummary")
        self.readout_label.setMinimumWidth(160)
        self.readout_label.setMaximumWidth(280)
        self.readout_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.measure_label = QtWidgets.QLabel("测量: --")
        self.measure_label.setObjectName("panelSummary")
        self.measure_label.setMinimumWidth(160)
        self.measure_label.setMaximumWidth(320)
        self.measure_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        preset_label = QtWidgets.QLabel("预设")
        preset_label.setObjectName("panelFieldLabel")
        window_label = QtWidgets.QLabel("时间窗口")
        window_label.setObjectName("panelFieldLabel")
        self.pause_btn.setProperty("secondaryRole", True)
        self.clear_btn.setProperty("dangerRole", True)
        self.focus_btn.setProperty("accentRole", True)
        row1.addWidget(self.pause_btn)
        row1.addWidget(self.clear_btn)
        row1.addWidget(preset_label)
        row1.addWidget(self.preset_combo)
        row1.addWidget(window_label)
        row1.addWidget(self.window_spin)
        row1.addWidget(self.follow_latest_cb)
        row1.addWidget(self.focus_btn)
        row1.addWidget(self.more_tools_btn)
        row1.addWidget(self.annotation_cb)
        row1.addStretch(1)
        row1.addWidget(self.readout_label, 1)
        row1.addWidget(self.measure_label, 1)
        tool_layout.addWidget(self._wrap_toolbar_row(row1_widget))
        self.pan_left_btn = QtWidgets.QPushButton("左移")
        self.pan_right_btn = QtWidgets.QPushButton("右移")
        self.zoom_in_btn = QtWidgets.QPushButton("时间放大")
        self.zoom_out_btn = QtWidgets.QPushButton("时间缩小")
        self.view_back_btn = QtWidgets.QPushButton("后退视图")
        self.view_forward_btn = QtWidgets.QPushButton("前进视图")
        self.latest_btn = QtWidgets.QPushButton("回到最新")
        self.fit_y_btn = QtWidgets.QPushButton("适配Y")
        self.mouse_mode_combo = QtWidgets.QComboBox()
        self.mouse_mode_combo.addItem("平移拖拽", "pan")
        self.mouse_mode_combo.addItem("框选缩放", "rect")
        self.cursor_cb = QtWidgets.QCheckBox("十字光标")
        self.clear_annotation_btn = QtWidgets.QPushButton("清空标签")
        self.measurement_cb = QtWidgets.QCheckBox("双游标测量")
        self.measure_channel_combo = QtWidgets.QComboBox()
        self.measure_channel_combo.setMinimumWidth(150)
        self.capture_a_btn = QtWidgets.QPushButton("A到当前")
        self.capture_b_btn = QtWidgets.QPushButton("B到当前")
        self.reset_measure_btn = QtWidgets.QPushButton("重置游标")
        self.export_image_btn = QtWidgets.QPushButton("导出图片")
        self.export_csv_btn = QtWidgets.QPushButton("导出 CSV")
        self.latest_btn.setProperty("accentRole", True)
        self.fit_y_btn.setProperty("secondaryRole", True)
        self.export_image_btn.setProperty("secondaryRole", True)
        self.export_csv_btn.setProperty("secondaryRole", True)

        row2_widget = QtWidgets.QWidget()
        row2 = QtWidgets.QHBoxLayout(row2_widget)
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(8)
        interaction_label = QtWidgets.QLabel("交互")
        interaction_label.setObjectName("panelFieldLabel")
        measure_channel_label = QtWidgets.QLabel("测量通道")
        measure_channel_label.setObjectName("panelFieldLabel")
        export_label = QtWidgets.QLabel("导出")
        export_label.setObjectName("panelFieldLabel")
        for hidden_widget in (
            self.pan_left_btn,
            self.pan_right_btn,
            self.zoom_in_btn,
            self.zoom_out_btn,
            self.view_back_btn,
            self.view_forward_btn,
            self.latest_btn,
            self.fit_y_btn,
            self.mouse_mode_combo,
        ):
            hidden_widget.setParent(row2_widget)
            hidden_widget.hide()
        row2.addWidget(interaction_label)
        row2.addWidget(self.cursor_cb)
        row2.addWidget(self.measurement_cb)
        row2.addWidget(self.clear_annotation_btn)
        row2.addSpacing(8)
        row2.addWidget(measure_channel_label)
        row2.addWidget(self.measure_channel_combo)
        row2.addWidget(self.capture_a_btn)
        row2.addWidget(self.capture_b_btn)
        row2.addWidget(self.reset_measure_btn)
        row2.addSpacing(8)
        row2.addWidget(export_label)
        row2.addWidget(self.export_image_btn)
        row2.addWidget(self.export_csv_btn)
        row2.addStretch(1)

        self.tool_detail_scroll = self._wrap_toolbar_row(row2_widget)
        self.tool_detail_scroll.setVisible(False)
        tool_layout.addWidget(self.tool_detail_scroll)
        self._root_layout.addWidget(tool_widget)

        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.22)
        self.plot.addLegend(colCount=2)
        self.plot.setLabel("bottom", "时间", units="s")
        self.plot.setLabel("left", "数值")
        self.plot.setLabel("right", "扰动")
        self.plot.setBackground("#0f172a")
        self.plot.setClipToView(True)
        self._root_layout.addWidget(self.plot, 1)

        self._plot_item = self.plot.getPlotItem()
        self._view_box = self.plot.getViewBox()
        self._disturbance_view = pg.ViewBox(enableMenu=False)
        self._disturbance_view.setMouseEnabled(x=False, y=False)
        self._plot_item.showAxis("right")
        self._plot_item.scene().addItem(self._disturbance_view)
        self._plot_item.getAxis("right").linkToView(self._disturbance_view)
        self._disturbance_view.setXLink(self._plot_item)
        self._view_box.sigResized.connect(self._sync_disturbance_view_geometry)
        if hasattr(self._view_box, "sigRangeChanged"):
            self._view_box.sigRangeChanged.connect(self._on_view_range_changed)
        self._sync_disturbance_view_geometry()
        self._view_box.setMouseEnabled(x=True, y=True)
        self._localize_context_menus()
        if hasattr(self._view_box, "sigRangeChangedManually"):
            self._view_box.sigRangeChangedManually.connect(self._on_manual_range_changed)

        self._cursor_v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen((210, 220, 235, 160), width=1))
        self._cursor_h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen((210, 220, 235, 120), width=1))
        self._cursor_v_line.hide()
        self._cursor_h_line.hide()
        self.plot.addItem(self._cursor_v_line, ignoreBounds=True)
        self.plot.addItem(self._cursor_h_line, ignoreBounds=True)
        self._mouse_proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=60, slot=self._on_mouse_moved)
        self.plot.scene().sigMouseClicked.connect(self._on_plot_clicked)

        self._measure_line_a = pg.InfiniteLine(
            angle=90,
            movable=True,
            pen=pg.mkPen("#fbbf24", width=2),
            label="A",
            labelOpts={"position": 0.92, "color": "#fbbf24", "fill": (18, 24, 38, 180)},
        )
        self._measure_line_b = pg.InfiniteLine(
            angle=90,
            movable=True,
            pen=pg.mkPen("#38bdf8", width=2),
            label="B",
            labelOpts={"position": 0.92, "color": "#38bdf8", "fill": (18, 24, 38, 180)},
        )
        self._measure_line_a.hide()
        self._measure_line_b.hide()
        self.plot.addItem(self._measure_line_a, ignoreBounds=True)
        self.plot.addItem(self._measure_line_b, ignoreBounds=True)
        self._measure_line_a.sigPositionChanged.connect(self._update_measurement_readout)
        self._measure_line_b.sigPositionChanged.connect(self._update_measurement_readout)

        self.channel_box = QtWidgets.QFrame()
        self.channel_box.setObjectName("channelControlPanel")
        self.channel_box_layout = QtWidgets.QVBoxLayout(self.channel_box)
        self.channel_box_layout.setContentsMargins(0, 0, 0, 0)
        self.channel_box_layout.setSpacing(10)

        channel_header = QtWidgets.QFrame()
        channel_header.setObjectName("panelHero")
        channel_header_layout = QtWidgets.QHBoxLayout(channel_header)
        channel_header_layout.setContentsMargins(10, 8, 10, 8)
        channel_header_layout.setSpacing(10)

        channel_header_text = QtWidgets.QVBoxLayout()
        channel_header_text.setSpacing(2)
        channel_eyebrow = QtWidgets.QLabel("通道")
        channel_eyebrow.setObjectName("panelEyebrow")
        channel_title = QtWidgets.QLabel("波形通道")
        channel_title.setObjectName("panelHeroTitle")
        channel_subtitle = QtWidgets.QLabel("管理波形通道与运行时扩展项。")
        channel_subtitle.setObjectName("panelHeroSubtitle")
        channel_subtitle.setWordWrap(True)
        channel_header_text.addWidget(channel_eyebrow)
        channel_header_text.addWidget(channel_title)
        channel_header_text.addWidget(channel_subtitle)
        channel_header_layout.addLayout(channel_header_text, 1)

        self.channel_summary_label = QtWidgets.QLabel("默认视图 · 0 / 0")
        self.channel_summary_label.setObjectName("panelSummary")
        self.channel_summary_label.setAlignment(QtCore.Qt.AlignCenter)
        self.channel_summary_label.setMinimumWidth(124)
        channel_header_layout.addWidget(self.channel_summary_label, 0, QtCore.Qt.AlignTop)
        self.channel_box_layout.addWidget(channel_header)

        channel_content = QtWidgets.QFrame()
        channel_content.setObjectName("panelCard")
        channel_content_layout = QtWidgets.QVBoxLayout(channel_content)
        channel_content_layout.setContentsMargins(10, 8, 10, 8)
        channel_content_layout.setSpacing(8)
        self.channel_grid_widget = QtWidgets.QWidget()
        self.channel_grid_widget.setObjectName("channelGridHost")
        self.channel_layout = QtWidgets.QGridLayout(self.channel_grid_widget)
        self.channel_layout.setContentsMargins(0, 0, 0, 0)
        self.channel_layout.setHorizontalSpacing(10)
        self.channel_layout.setVerticalSpacing(6)
        channel_content_layout.addWidget(self.channel_grid_widget)
        self.channel_box_layout.addWidget(channel_content)
        self._root_layout.addWidget(self.channel_box)

        self.pause_btn.clicked.connect(self._toggle_pause)
        self.clear_btn.clicked.connect(self.clear)
        self.window_spin.valueChanged.connect(self._set_window_sec)
        self.preset_combo.currentIndexChanged.connect(self._apply_selected_preset)
        self.follow_latest_cb.toggled.connect(self._on_follow_latest_changed)
        self.pan_left_btn.clicked.connect(lambda: self._pan_x(-0.35))
        self.pan_right_btn.clicked.connect(lambda: self._pan_x(0.35))
        self.zoom_in_btn.clicked.connect(lambda: self._change_window(0.8))
        self.zoom_out_btn.clicked.connect(lambda: self._change_window(1.25))
        self.view_back_btn.clicked.connect(lambda: self.navigate_view_history(-1))
        self.view_forward_btn.clicked.connect(lambda: self.navigate_view_history(1))
        self.latest_btn.clicked.connect(self.focus_latest)
        self.focus_btn.clicked.connect(self.focus_current_view)
        self.fit_y_btn.clicked.connect(self.fit_y_to_visible)
        self.mouse_mode_combo.currentIndexChanged.connect(self._on_mouse_mode_changed)
        self.cursor_cb.toggled.connect(self._toggle_cursor)
        self.measurement_cb.toggled.connect(self._toggle_measurement)
        self.measure_channel_combo.currentIndexChanged.connect(self._update_measurement_readout)
        self.more_tools_btn.toggled.connect(self.tool_detail_scroll.setVisible)
        self.capture_a_btn.clicked.connect(lambda: self._capture_measure_cursor("a"))
        self.capture_b_btn.clicked.connect(lambda: self._capture_measure_cursor("b"))
        self.reset_measure_btn.clicked.connect(self._reset_measurement_lines)
        self.export_image_btn.clicked.connect(self.export_plot_image)
        self.export_csv_btn.clicked.connect(self.export_visible_csv)
        self.clear_annotation_btn.clicked.connect(self.clear_point_markers)

        self.pause_btn.setToolTip("暂停/继续实时绘制")
        self.pan_left_btn.setToolTip("向历史方向平移当前时间窗口")
        self.pan_right_btn.setToolTip("向最新方向平移当前时间窗口")
        self.zoom_in_btn.setToolTip("缩小时间窗口，放大时间轴")
        self.zoom_out_btn.setToolTip("扩大时间窗口，查看更长历史")
        self.view_back_btn.setToolTip("返回上一个视图范围")
        self.view_forward_btn.setToolTip("前进到下一个视图范围")
        self.latest_btn.setToolTip("立刻回到最新数据位置并继续实时跟随")
        self.focus_btn.setToolTip("回到最新数据并自动聚焦当前可见曲线")
        self.fit_y_btn.setToolTip("根据当前时间窗口内的可见曲线自动适配 Y 轴")
        self.measurement_cb.setToolTip("开启可拖动的双游标，用于测量时间差和幅值差")
        self.capture_a_btn.setToolTip("将游标 A 吸附到当前十字光标位置")
        self.capture_b_btn.setToolTip("将游标 B 吸附到当前十字光标位置")
        self.reset_measure_btn.setToolTip("将双游标重置到当前时间窗口的 25% 和 75% 位置")
        self.export_image_btn.setToolTip("导出当前波形视图为 PNG 图片")
        self.export_csv_btn.setToolTip("导出当前时间窗口内的可见曲线数据为 CSV")
        self.annotation_cb.setToolTip("开启后，左键点击波形添加标签，右键点击标签删除")
        self.clear_annotation_btn.setToolTip("清除当前所有点击标签")
        self._toggle_measurement(False)

    def _localize_context_menus(self):
        plot_item = self.plot.getPlotItem()
        self._translate_menu(plot_item.vb.menu, self.VIEWBOX_MENU_TEXTS)
        self._translate_widget_tree(plot_item.vb.menu, self.VIEWBOX_WIDGET_TEXTS)
        self._translate_menu(plot_item.ctrlMenu, self.PLOT_MENU_TEXTS)
        self._translate_widget_tree(plot_item.ctrlMenu, self.PLOT_WIDGET_TEXTS)
        scene = self.plot.scene()
        for action in getattr(scene, "contextMenu", []):
            translated = self.SCENE_MENU_TEXTS.get(action.text())
            if translated:
                action.setText(translated)

    def _translate_menu(self, menu: QtWidgets.QMenu, translations: Dict[str, str]):
        title = translations.get(menu.title())
        if title:
            menu.setTitle(title)
        for action in menu.actions():
            translated_text = translations.get(action.text())
            if translated_text:
                action.setText(translated_text)
            if action.menu() is not None:
                self._translate_menu(action.menu(), translations)

    def _translate_widget_tree(self, parent: QtWidgets.QWidget, translations: Dict[str, str]):
        for widget in parent.findChildren(QtWidgets.QWidget):
            translated_text = translations.get(widget.objectName())
            if not translated_text:
                continue
            if isinstance(widget, QtWidgets.QAbstractButton):
                widget.setText(translated_text)
            elif isinstance(widget, QtWidgets.QLabel):
                widget.setText(translated_text)
            elif isinstance(widget, QtWidgets.QGroupBox):
                widget.setTitle(translated_text)

    def _init_channels(self):
        specs = [
            ("ref", "#38bdf8"),
            ("feedback", "#22c55e"),
            ("u_cmd", "#f97316"),
            ("disturbance_sim", "#14b8a6"),
            ("v1", "#facc15"),
            ("v2", "#f59e0b"),
            ("z1", "#8b5cf6"),
            ("z2", "#6366f1"),
            ("z3", "#ec4899"),
            ("roll", "#eab308"),
            ("pitch", "#a78bfa"),
            ("yaw", "#f43f5e"),
        ]
        for name, color in specs:
            self._add_channel(name, color, name in self.DEFAULT_VISIBLE_CHANNELS)

    def _add_channel(self, name: str, color: str, checked: bool):
        display_name = self._channel_display_name(name)
        control_zh, control_en = self._channel_control_labels(name, display_name)
        if self._is_disturbance_channel(name):
            curve = pg.PlotCurveItem([], [], pen=pg.mkPen(color=color, width=1.8), name=display_name)
            self._disturbance_view.addItem(curve)
            legend = self.plot.plotItem.legend
            if legend is not None:
                legend.addItem(curve, display_name)
        else:
            curve = self.plot.plot([], [], pen=pg.mkPen(color=color, width=1.8), name=display_name)
        curve.setVisible(checked)
        checkbox = QtWidgets.QCheckBox(control_zh)
        checkbox.setChecked(checked)
        checkbox.toggled.connect(lambda on, ch=name: self.set_channel_visible(ch, on))
        english_label = QtWidgets.QLabel(control_en)
        english_label.setObjectName("statusHint")
        english_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        english_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        english_label.setFixedWidth(150)
        self._set_english_label_text(english_label, control_en)
        self._channels[name] = {
            "curve": curve,
            "x": deque(maxlen=self.max_points),
            "y": deque(maxlen=self.max_points),
            "visible": checked,
            "checkbox": checkbox,
            "english_label": english_label,
            "dynamic": bool(name in self._dynamic_algorithm_channels),
        }

    def _is_disturbance_channel(self, name: str) -> bool:
        return str(name) in self.DISTURBANCE_CHANNELS

    def _should_smooth_channel(self, channel_name: str) -> bool:
        return str(channel_name) not in self.DISPLAY_SMOOTHING_EXCLUDED

    def _smoothed_series(self, channel_name: str, x_values: List[float], y_values: List[float]) -> Tuple[List[float], List[float]]:
        if not self._should_smooth_channel(channel_name):
            return x_values, y_values
        if len(y_values) < 3:
            return x_values, y_values

        radius = len(self.DISPLAY_SMOOTHING_WEIGHTS) // 2
        smoothed: List[float] = []
        for index, current in enumerate(y_values):
            if not math.isfinite(float(current)):
                smoothed.append(float("nan"))
                continue

            weighted_sum = 0.0
            weight_total = 0.0
            for offset, weight in enumerate(self.DISPLAY_SMOOTHING_WEIGHTS):
                sample_index = index + offset - radius
                if sample_index < 0 or sample_index >= len(y_values):
                    continue
                sample = y_values[sample_index]
                if not math.isfinite(float(sample)):
                    continue
                weighted_sum += float(sample) * float(weight)
                weight_total += float(weight)
            if weight_total <= 0.0:
                smoothed.append(float(current))
            else:
                smoothed.append(weighted_sum / weight_total)
        return x_values, smoothed

    def _refresh_channel_curve(self, channel_name: str):
        channel = self._channels.get(channel_name)
        if channel is None:
            return
        x_values = list(channel["x"])
        y_values = list(channel["y"])
        if not x_values:
            channel["curve"].setData([], [])
            return
        display_x, display_y = self._smoothed_series(channel_name, x_values, y_values)
        channel["curve"].setData(display_x, display_y)

    def _channel_display_name(self, channel_name: str) -> str:
        if channel_name in self.ALGORITHM_CHANNELS or channel_name in self._dynamic_algorithm_channels:
            override = self._algorithm_channel_labels.get(channel_name)
            if isinstance(override, str) and override.strip():
                return override.strip()
        return self.CHANNEL_LABELS.get(channel_name, channel_name)

    def _channel_control_labels(self, channel_name: str, display_name: str | None = None) -> Tuple[str, str]:
        english_label = self._algorithm_channel_labels.get(channel_name, channel_name)
        if not isinstance(english_label, str) or not english_label.strip():
            english_label = str(channel_name)
        english_label = english_label.strip()

        current_checkbox = None
        if channel_name in self._channels:
            current_checkbox = self._channels[channel_name]["checkbox"].text()

        if channel_name == "disturbance_sim" and isinstance(display_name, str) and display_name.strip():
            return display_name.strip(), english_label

        chinese_label = self.CHANNEL_LABELS.get(channel_name)
        if isinstance(chinese_label, str) and chinese_label.strip():
            return chinese_label.strip(), english_label

        if isinstance(current_checkbox, str) and current_checkbox.strip() and self._contains_cjk(current_checkbox):
            return current_checkbox.strip(), english_label

        fallback = display_name if isinstance(display_name, str) and display_name.strip() else english_label
        fallback = str(fallback).strip()
        if not self._contains_cjk(fallback):
            fallback = f"字段 {fallback}"
        return fallback, english_label

    def _set_english_label_text(self, label: QtWidgets.QLabel, full_text: str):
        text = str(full_text).strip()
        label.setToolTip(text)
        metrics = label.fontMetrics()
        label.setText(metrics.elidedText(text, QtCore.Qt.ElideRight, 140))

    def _next_dynamic_channel_color(self) -> str:
        index = len(self._dynamic_algorithm_channels) % len(self.DYNAMIC_CHANNEL_COLORS)
        return self.DYNAMIC_CHANNEL_COLORS[index]

    def _is_dynamic_algorithm_channel(self, channel_name: str) -> bool:
        return str(channel_name) in self._dynamic_algorithm_channels

    @staticmethod
    def _contains_cjk(text: str) -> bool:
        for char in str(text):
            if "\u4e00" <= char <= "\u9fff":
                return True
        return False

    def _should_create_dynamic_algorithm_channel(self, channel_name: str) -> bool:
        name = str(channel_name).strip()
        if not name or name.startswith("_"):
            return False
        if name in self._channels:
            return False
        if name in self.COMMON_CHANNELS or name in self.ALGORITHM_CHANNELS:
            return False
        return True

    def _default_dynamic_channel_visibility(self) -> bool:
        preset_key = self.current_preset_key()
        return preset_key == "all"

    def _set_channel_visible_silently(self, channel_name: str, visible: bool):
        if channel_name not in self._channels:
            return
        control = self._channels[channel_name]["checkbox"]
        blocker = QtCore.QSignalBlocker(control)
        control.setChecked(bool(visible))
        del blocker
        self.set_channel_visible(channel_name, bool(visible))

    def _apply_balance_runtime_visibility(self):
        if self.current_preset_key() != "balance":
            return
        for channel_name in self.BALANCE_RUNTIME_CHANNELS:
            if channel_name in self._channels:
                self._set_channel_visible_silently(channel_name, False)
        for channel_name in self._dynamic_algorithm_channels:
            if channel_name in self._channels:
                self._set_channel_visible_silently(channel_name, False)

    def set_runtime_channel_expanded(self, expanded: bool):
        expanded = bool(expanded)
        if self._runtime_channel_expanded == expanded:
            return
        self._runtime_channel_expanded = expanded
        if not expanded and self.current_preset_key() == "balance":
            for channel_name in self.BALANCE_RUNTIME_CHANNELS:
                if channel_name in self._channels:
                    self._set_channel_visible_silently(channel_name, False)
            for channel_name in self._dynamic_algorithm_channels:
                if channel_name in self._channels:
                    self._set_channel_visible_silently(channel_name, False)
        self._reflow_channel_layout()

    def _ensure_dynamic_algorithm_channel(self, channel_name: str):
        if not self._should_create_dynamic_algorithm_channel(channel_name):
            return
        color = self._next_dynamic_channel_color()
        self._dynamic_algorithm_channels.append(str(channel_name))
        self._add_channel(str(channel_name), color, self._default_dynamic_channel_visibility())
        self._reflow_channel_layout()
        self._populate_measure_channel_combo()

    def _dynamic_channel_group(self, channel_name: str) -> str:
        name = str(channel_name).strip().lower()
        tokens = [token for token in name.replace("-", "_").split("_") if token]
        if any("err" in token or "error" in token for token in tokens):
            return "error"
        if name.endswith("out") or any(token in {"out", "output", "cmd", "control", "ctrl"} for token in tokens):
            return "output"
        return "state"

    def _ordered_dynamic_channel_names(self) -> List[str]:
        grouped: Dict[str, List[str]] = {key: [] for key in self.DYNAMIC_GROUP_ORDER}
        extras: List[str] = []
        for channel_name in self._dynamic_algorithm_channels:
            group_key = self._dynamic_channel_group(channel_name)
            if group_key in grouped:
                grouped[group_key].append(channel_name)
            else:
                extras.append(channel_name)
        ordered: List[str] = []
        for group_key in self.DYNAMIC_GROUP_ORDER:
            ordered.extend(grouped[group_key])
        ordered.extend(extras)
        return ordered

    def _ordered_channel_names(self) -> List[str]:
        ordered: List[str] = []
        leading = self.DEFAULT_CHANNEL_ORDER + self.LOCAL_CHANNEL_ORDER + self.REMOTE_FIXED_CHANNEL_ORDER
        tail = [name for name in self.CHANNEL_DISPLAY_ORDER if name not in leading]
        for channel_name in leading:
            if channel_name in self._channels:
                ordered.append(channel_name)
        for channel_name in self._ordered_dynamic_channel_names():
            if channel_name in self._channels and channel_name not in ordered:
                ordered.append(channel_name)
        for channel_name in tail:
            if channel_name in self._channels and channel_name not in ordered:
                ordered.append(channel_name)
        for channel_name in self._channels.keys():
            if channel_name not in ordered:
                ordered.append(channel_name)
        return ordered

    def _update_channel_summary(self):
        if not hasattr(self, "channel_summary_label"):
            return
        total_count = len(self._channels)
        visible_count = sum(1 for channel in self._channels.values() if channel["visible"])
        mode_text = "运行扩展" if self._runtime_channel_expanded else "默认视图"
        dynamic_count = len(self._dynamic_algorithm_channels)
        if dynamic_count > 0:
            summary = f"{mode_text} · {visible_count} / {total_count} · 动态 {dynamic_count}"
        else:
            summary = f"{mode_text} · {visible_count} / {total_count}"
        self.channel_summary_label.setText(summary)

    def _reflow_channel_layout(self):
        for header in self._channel_section_headers:
            header.deleteLater()
        self._channel_section_headers.clear()
        while self.channel_layout.count():
            item = self.channel_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(self.channel_grid_widget)

        row = 0

        def add_column_headers():
            nonlocal row
            left_label = QtWidgets.QLabel("中文通道")
            right_label = QtWidgets.QLabel("English")
            left_label.setObjectName("panelTableHeader")
            right_label.setObjectName("panelTableHeader")
            self.channel_layout.addWidget(left_label, row, 0)
            self.channel_layout.addWidget(right_label, row, 1)
            self._channel_section_headers.extend([left_label, right_label])
            row += 1

        def add_channel_row(channel_name: str):
            nonlocal row
            channel = self._channels.get(channel_name)
            if not channel:
                return
            self.channel_layout.addWidget(channel["checkbox"], row, 0)
            self.channel_layout.addWidget(channel["english_label"], row, 1)
            row += 1

        def add_section(title: str):
            nonlocal row
            label = QtWidgets.QLabel(title)
            label.setObjectName("panelSectionHeader")
            self.channel_layout.addWidget(label, row, 0, 1, 2)
            self._channel_section_headers.append(label)
            row += 1

        def add_section_channels(channel_names: List[str]):
            for channel_name in channel_names:
                add_channel_row(channel_name)

        add_column_headers()
        default_channels = [name for name in self.DEFAULT_CHANNEL_ORDER if name in self._channels]
        if default_channels:
            add_section(self.STATIC_SECTION_TITLES["default"])
            add_section_channels(default_channels)

        if self._runtime_channel_expanded:
            local_channels = [name for name in self.LOCAL_CHANNEL_ORDER if name in self._channels]
            if local_channels:
                add_section(self.STATIC_SECTION_TITLES["local"])
                add_section_channels(local_channels)

            remote_fixed_channels = [name for name in self.REMOTE_FIXED_CHANNEL_ORDER if name in self._channels]
            remote_dynamic_channels = self._ordered_dynamic_channel_names()
            if remote_fixed_channels or remote_dynamic_channels:
                add_section(self.STATIC_SECTION_TITLES["remote"])
                add_section_channels(remote_fixed_channels + remote_dynamic_channels)

            static_known = set(self.DEFAULT_CHANNEL_ORDER + self.LOCAL_CHANNEL_ORDER + self.REMOTE_FIXED_CHANNEL_ORDER)
            tail = [name for name in self.CHANNEL_DISPLAY_ORDER if name not in static_known and name not in self._dynamic_algorithm_channels]
            add_section_channels([channel_name for channel_name in tail if channel_name in self._channels])

            for channel_name in self._channels.keys():
                if channel_name in static_known or channel_name in self._dynamic_algorithm_channels or channel_name in tail:
                    continue
                add_section_channels([channel_name])

        self._update_channel_summary()

    def _sync_disturbance_view_geometry(self):
        self._disturbance_view.setGeometry(self._view_box.sceneBoundingRect())
        self._disturbance_view.linkedViewChanged(self._view_box, self._disturbance_view.XAxis)

    def _on_view_range_changed(self, *args):
        self._sync_disturbance_view_geometry()
        self._fit_disturbance_y_to_visible()

    def _update_disturbance_axis_visibility(self):
        any_visible = any(
            self._channels[name]["visible"]
            for name in self.DISTURBANCE_CHANNELS
            if name in self._channels
        )
        self._plot_item.showAxis("right", any_visible)
        self._fit_disturbance_y_to_visible()

    def _collect_visible_disturbance_y_in_current_x_range(self) -> List[float]:
        x_start, x_end = self._current_x_range()
        values: List[float] = []
        for channel_name in self.DISTURBANCE_CHANNELS:
            channel = self._channels.get(channel_name)
            if not channel or not channel["visible"] or not channel["x"]:
                continue
            xs = list(channel["x"])
            ys = list(channel["y"])
            scoped = [
                y for x, y in zip(xs, ys)
                if x_start <= x <= x_end and math.isfinite(float(y))
            ]
            if not scoped:
                scoped = [y for y in ys if math.isfinite(float(y))]
            values.extend(scoped)
        return values

    def _fit_disturbance_y_to_visible(self):
        y_values = self._collect_visible_disturbance_y_in_current_x_range()
        if not y_values:
            self._disturbance_view.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
            return
        y_min = min(y_values)
        y_max = max(y_values)
        if abs(y_max - y_min) < 1e-6:
            pad = max(0.1, abs(y_max) * 0.2 + 0.1)
            y_min -= pad
            y_max += pad
        else:
            pad = (y_max - y_min) * 0.18
            y_min -= pad
            y_max += pad
        self._disturbance_view.setYRange(y_min, y_max, padding=0.0)

    def _install_shortcuts(self):
        shortcuts = [
            ("Ctrl+Space", self._toggle_pause),
            ("Ctrl+Home", self.focus_latest),
            ("Ctrl+Shift+F", self.focus_current_view),
            ("Ctrl+Alt+F", self.fit_y_to_visible),
            ("Ctrl+Left", lambda: self._pan_x(-0.35)),
            ("Ctrl+Right", lambda: self._pan_x(0.35)),
            ("Alt+Left", lambda: self.navigate_view_history(-1)),
            ("Alt+Right", lambda: self.navigate_view_history(1)),
            ("Ctrl+Shift+M", lambda: self.measurement_cb.toggle()),
            ("Ctrl+Shift+S", self.export_plot_image),
        ]
        for sequence, callback in shortcuts:
            shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(sequence), self)
            shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)

    def _populate_measure_channel_combo(self):
        current_key = self.measure_channel_combo.currentData() if hasattr(self, "measure_channel_combo") else None
        blocker = QtCore.QSignalBlocker(self.measure_channel_combo)
        self.measure_channel_combo.clear()
        for channel_name in self._ordered_channel_names():
            channel = self._channels.get(channel_name)
            if channel is None:
                continue
            self.measure_channel_combo.addItem(self._channel_display_name(channel_name), channel_name)
        target = self.measure_channel_combo.findData(current_key if current_key is not None else "feedback")
        if target < 0:
            target = 0
        self.measure_channel_combo.setCurrentIndex(target)
        del blocker

    def measurement_channel_items(self):
        return [
            (self.measure_channel_combo.itemText(index), self.measure_channel_combo.itemData(index))
            for index in range(self.measure_channel_combo.count())
        ]

    def current_measure_channel(self):
        return self.measure_channel_combo.currentData()

    def set_measure_channel(self, channel_name: str):
        index = self.measure_channel_combo.findData(channel_name)
        if index >= 0:
            self.measure_channel_combo.setCurrentIndex(index)

    def current_mouse_mode(self):
        return self.mouse_mode_combo.currentData()

    def set_mouse_mode_key(self, mode_key: str):
        index = self.mouse_mode_combo.findData(mode_key)
        if index >= 0:
            self.mouse_mode_combo.setCurrentIndex(index)

    def is_cursor_enabled(self):
        return self.cursor_cb.isChecked()

    def set_cursor_enabled(self, enabled: bool):
        self.cursor_cb.setChecked(enabled)

    def is_annotation_enabled(self):
        return self.annotation_cb.isChecked()

    def set_annotation_enabled(self, enabled: bool):
        self.annotation_cb.setChecked(enabled)

    def is_measurement_enabled(self):
        return self.measurement_cb.isChecked()

    def set_measurement_enabled(self, enabled: bool):
        self.measurement_cb.setChecked(enabled)

    def current_preset_key(self):
        return self.preset_combo.currentData()

    def set_preset_key(self, preset_key: str):
        index = self.preset_combo.findData(preset_key)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)

    def get_state(self) -> dict:
        return {
            "window_sec": float(self.window_sec),
            "preset": self.current_preset_key(),
            "follow_latest": self.follow_latest_cb.isChecked(),
            "mouse_mode": self.current_mouse_mode(),
            "cursor_enabled": self.is_cursor_enabled(),
            "annotation_enabled": self.is_annotation_enabled(),
            "measurement_enabled": self.is_measurement_enabled(),
            "measure_channel": self.current_measure_channel(),
            "channels": {name: bool(channel["visible"]) for name, channel in self._channels.items()},
        }

    def apply_state(self, state: dict):
        if not isinstance(state, dict):
            return

        if "window_sec" in state:
            try:
                self.window_spin.setValue(float(state.get("window_sec", self.window_sec)))
            except (TypeError, ValueError):
                pass

        preset_key = state.get("preset")
        if preset_key is not None:
            self.set_preset_key(str(preset_key))

        channel_state = state.get("channels")
        if isinstance(channel_state, dict):
            for channel_name, visible in channel_state.items():
                if channel_name not in self._channels:
                    continue
                self._set_channel_visible_silently(channel_name, bool(visible))

        if "follow_latest" in state:
            self.follow_latest_cb.setChecked(bool(state.get("follow_latest")))
        if "mouse_mode" in state:
            self.set_mouse_mode_key(str(state.get("mouse_mode")))
        if "cursor_enabled" in state:
            self.set_cursor_enabled(bool(state.get("cursor_enabled")))
        if "annotation_enabled" in state:
            self.set_annotation_enabled(bool(state.get("annotation_enabled")))
        if "measurement_enabled" in state:
            self.set_measurement_enabled(bool(state.get("measurement_enabled")))
        if "measure_channel" in state:
            self.set_measure_channel(str(state.get("measure_channel")))

    def reset_to_defaults(self):
        if self._paused:
            self._toggle_pause()
        self.window_spin.setValue(20.0)
        self.set_preset_key("balance")
        self.follow_latest_cb.setChecked(True)
        self.set_mouse_mode_key("pan")
        self.set_cursor_enabled(False)
        self.set_annotation_enabled(False)
        self.set_measurement_enabled(False)
        self.set_measure_channel("feedback")
        self.clear_point_markers()

    def take_channel_widget(self) -> QtWidgets.QWidget:
        if not self._channel_widget_detached:
            self._root_layout.removeWidget(self.channel_box)
            self.channel_box.setParent(None)
            self._channel_widget_detached = True
        return self.channel_box

    def _toggle_pause(self):
        self._paused = not self._paused
        self.pause_btn.setText("继续" if self._paused else "暂停")

    def apply_theme(self, theme: dict):
        self._theme = {**self._default_theme(), **(theme or {})}

        self.plot.setBackground(self._theme["plot_background"])
        self.plot.showGrid(x=True, y=True, alpha=float(self._theme["plot_grid_alpha"]))
        self.plot.setLabel("bottom", "时间", units="s", color=self._theme["plot_text"])
        self.plot.setLabel("left", "数值", color=self._theme["plot_text"])
        self.plot.setLabel("right", "扰动", color=self._theme["plot_text"])
        for axis_name in ("left", "bottom", "right"):
            axis = self.plot.getAxis(axis_name)
            axis.setPen(pg.mkPen(self._theme["plot_axis"], width=1))
            axis.setTextPen(pg.mkPen(self._theme["plot_text"]))

        legend = self.plot.plotItem.legend
        if legend is not None:
            for _, label in legend.items:
                try:
                    label.item.setDefaultTextColor(QtGui.QColor(self._theme["plot_text"]))
                except Exception:
                    pass

        cursor_rgba = tuple(int(v) for v in self._theme["plot_cursor"])
        cursor_h_rgba = cursor_rgba[:3] + (max(60, int(cursor_rgba[3] * 0.75)),)
        self._cursor_v_line.setPen(pg.mkPen(cursor_rgba, width=1))
        self._cursor_h_line.setPen(pg.mkPen(cursor_h_rgba, width=1))

        self._measure_line_a.setPen(pg.mkPen(self._theme["plot_measure_a"], width=2))
        self._measure_line_b.setPen(pg.mkPen(self._theme["plot_measure_b"], width=2))
        self._update_measure_label_style(self._measure_line_a, "A", self._theme["plot_measure_a"])
        self._update_measure_label_style(self._measure_line_b, "B", self._theme["plot_measure_b"])

        for marker_info in self._point_markers:
            marker_info["marker"].setPen(pg.mkPen(self._to_qcolor(self._theme["plot_annotation_border"]), width=1.6))
            marker_info["marker"].setBrush(pg.mkBrush(self._theme["plot_measure_a"]))
            marker_info["text"].setHtml(
                self._build_annotation_html(
                    marker_info["label"],
                    marker_info["x"],
                    marker_info["y"],
                )
            )

    def _update_measure_label_style(self, line: pg.InfiniteLine, label_text: str, color: str):
        line.label.setColor(color)
        line.label.fill = pg.mkBrush(self._to_qcolor(self._theme["plot_annotation_bg"]))
        line.label.border = pg.mkPen(self._to_qcolor(self._theme["plot_annotation_border"]))
        line.label.setFormat(label_text)
        line.label.update()

    def _build_annotation_html(self, label_text: str, x_value: float, y_value: float) -> str:
        return (
            "<div style='background-color: {bg}; color: {fg}; "
            "padding: 3px 7px; border: 1px solid {border}; border-radius: 3px; "
            "font-size: 11px; white-space: nowrap;'>"
            "<b>{label}</b> t={x:.3f}s v={y:.3f}</div>"
        ).format(
            bg=self._theme["plot_annotation_bg"],
            fg=self._theme["plot_annotation_text"],
            border=self._theme["plot_annotation_border"],
            label=label_text,
            x=x_value,
            y=y_value,
        )

    def _set_window_sec(self, value: float):
        self._updating_view += 1
        self._push_view_history()
        self.window_sec = float(value)
        if self.follow_latest_cb.isChecked():
            self._apply_latest_window()
        else:
            self._apply_window_around_current_center()
        self._push_view_history()
        self._updating_view -= 1

    def _apply_selected_preset(self):
        preset_key = self.preset_combo.currentData()
        if preset_key:
            self.apply_preset(preset_key)

    def _on_follow_latest_changed(self, checked: bool):
        if checked:
            self._updating_view += 1
            self._apply_latest_window()
            self._updating_view -= 1

    def _on_mouse_mode_changed(self):
        self._set_mouse_mode(self.mouse_mode_combo.currentData())

    def _set_mouse_mode(self, mode_key: str):
        if mode_key == "rect":
            self._view_box.setMouseMode(pg.ViewBox.RectMode)
        else:
            self._view_box.setMouseMode(pg.ViewBox.PanMode)

    def _toggle_cursor(self, enabled: bool):
        self._cursor_v_line.setVisible(enabled)
        self._cursor_h_line.setVisible(enabled)
        if not enabled:
            self.readout_label.setText("游标: --")

    def _on_mouse_moved(self, event):
        pos = event[0] if isinstance(event, tuple) else event
        if not self.plot.plotItem.sceneBoundingRect().contains(pos):
            if not self.cursor_cb.isChecked():
                self.readout_label.setText("游标: --")
            return
        mouse_point = self._view_box.mapSceneToView(pos)
        x_value = mouse_point.x()
        y_value = mouse_point.y()
        self._last_mouse_x = float(x_value)
        hovered = self._find_nearest_visible_point(pos, x_value, y_value)
        hovered_label = hovered[1] if hovered is not None else "--"
        if not self.cursor_cb.isChecked():
            self.readout_label.setText(f"悬停: {hovered_label}")
            return
        self._cursor_v_line.setPos(x_value)
        self._cursor_h_line.setPos(y_value)
        extras = self._nearest_visible_values(x_value)
        suffix = f" | {' | '.join(extras)}" if extras else ""
        self.readout_label.setText(f"游标: t={x_value:.2f}s, y={y_value:.3f} | 类型={hovered_label}{suffix}")

    def _on_plot_clicked(self, event):
        if not self.annotation_cb.isChecked():
            return
        if event.button() == QtCore.Qt.RightButton:
            self._try_remove_marker_at(event)
            return
        if event.button() != QtCore.Qt.LeftButton:
            return
        pos = event.scenePos()
        if not self.plot.plotItem.sceneBoundingRect().contains(pos):
            return
        mouse_point = self._view_box.mapSceneToView(pos)
        marker = self._find_nearest_visible_point(pos, mouse_point.x(), mouse_point.y())
        if marker is None:
            return
        self._add_point_marker(*marker)
        event.accept()

    def _try_remove_marker_at(self, event):
        pos = event.scenePos()
        if not self.plot.plotItem.sceneBoundingRect().contains(pos):
            return
        view_pos = self._view_box.mapSceneToView(pos)
        best_idx = None
        best_dist = float("inf")
        threshold = (self._view_box.viewRange()[1][1] - self._view_box.viewRange()[1][0]) * 0.04
        for i, info in enumerate(self._point_markers):
            dx = abs(info["x"] - view_pos.x())
            dy = abs(info["y"] - view_pos.y())
            dist = math.hypot(dx, dy)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        if best_idx is not None and best_dist < threshold:
            info = self._point_markers.pop(best_idx)
            self.plot.removeItem(info["marker"])
            self.plot.removeItem(info["text"])
            event.accept()

    def _find_nearest_visible_point(self, scene_pos, x_value: float, y_value: float):
        best = None
        best_score = None
        for channel_name, channel in self._channels.items():
            if not channel["visible"] or not channel["x"]:
                continue
            xs = list(channel["x"])
            ys = list(channel["y"])
            nearest_index = min(range(len(xs)), key=lambda idx: abs(xs[idx] - x_value))
            px = xs[nearest_index]
            py = ys[nearest_index]
            if self._is_disturbance_channel(channel_name):
                point = self._disturbance_view.mapViewToScene(QtCore.QPointF(float(px), float(py)))
            else:
                point = self._view_box.mapViewToScene(QtCore.QPointF(float(px), float(py)))
            dx = float(point.x() - scene_pos.x())
            dy = float(point.y() - scene_pos.y())
            score = dx * dx + dy * dy
            if best_score is None or score < best_score:
                best_score = score
                best = (channel_name, self._channel_display_name(channel_name), float(px), float(py))
        return best

    def _add_point_marker(self, channel_name: str, label_text: str, x_value: float, y_value: float):
        marker = pg.ScatterPlotItem(
            x=[x_value],
            y=[y_value],
            symbol="d",
            size=11,
            pen=pg.mkPen(self._to_qcolor(self._theme["plot_annotation_border"]), width=1.6),
            brush=pg.mkBrush(self._theme["plot_measure_a"]),
        )
        self.plot.addItem(marker)

        text_item = pg.TextItem(
            html=self._build_annotation_html(label_text, x_value, y_value),
            anchor=(0.5, 1.6),
        )
        text_item.setPos(x_value, y_value)
        self.plot.addItem(text_item)
        self._point_markers.append(
            {
                "marker": marker,
                "text": text_item,
                "channel": channel_name,
                "label": label_text,
                "x": float(x_value),
                "y": float(y_value),
            }
        )

        if len(self._point_markers) > 20:
            marker_info = self._point_markers.pop(0)
            self.plot.removeItem(marker_info["marker"])
            self.plot.removeItem(marker_info["text"])

    def clear_point_markers(self):
        while self._point_markers:
            marker_info = self._point_markers.pop()
            self.plot.removeItem(marker_info["marker"])
            self.plot.removeItem(marker_info["text"])

    def _nearest_visible_values(self, x_value: float) -> List[str]:
        parts = []
        for channel_name, channel in self._channels.items():
            if not channel["visible"] or not channel["x"]:
                continue
            xs = list(channel["x"])
            ys = list(channel["y"])
            nearest_index = min(range(len(xs)), key=lambda idx: abs(xs[idx] - x_value))
            label = self._channel_display_name(channel_name)
            parts.append(f"{label}={ys[nearest_index]:.3f}")
            if len(parts) >= 2:
                break
        return parts

    def _on_manual_range_changed(self, *args):
        if self._updating_view > 0:
            return
        if self.follow_latest_cb.isChecked():
            blocker = QtCore.QSignalBlocker(self.follow_latest_cb)
            self.follow_latest_cb.setChecked(False)
            del blocker
        self._push_view_history()

    def _change_window(self, factor: float):
        new_value = max(self.window_spin.minimum(), min(self.window_spin.maximum(), self.window_sec * factor))
        self.window_spin.setValue(new_value)

    def _pan_x(self, factor: float):
        if not self._has_data():
            return
        self._updating_view += 1
        self._push_view_history()
        step = self.window_sec * factor
        self._set_follow_latest(False)
        start, end = self._current_x_range()
        self._apply_time_range(start + step, end + step)
        self._push_view_history()
        self._updating_view -= 1

    def _set_follow_latest(self, enabled: bool):
        blocker = QtCore.QSignalBlocker(self.follow_latest_cb)
        self.follow_latest_cb.setChecked(enabled)
        del blocker

    def focus_latest(self):
        self._updating_view += 1
        self._push_view_history()
        self._set_follow_latest(True)
        self._apply_latest_window()
        self._push_view_history()
        self._updating_view -= 1

    def focus_current_view(self):
        self._updating_view += 1
        self._push_view_history()
        if self.follow_latest_cb.isChecked():
            self._apply_latest_window()
        self.fit_y_to_visible()
        self._push_view_history()
        self._updating_view -= 1

    def fit_y_to_visible(self):
        y_values = self._collect_visible_y_in_current_x_range()
        if not y_values:
            self._fit_disturbance_y_to_visible()
            return
        y_min = min(y_values)
        y_max = max(y_values)
        if abs(y_max - y_min) < 1e-6:
            pad = max(0.5, abs(y_max) * 0.1 + 0.5)
            y_min -= pad
            y_max += pad
        else:
            pad = (y_max - y_min) * 0.05
            y_min -= pad
            y_max += pad
        self._updating_view += 1
        self.plot.setYRange(y_min, y_max, padding=0.0)
        self._fit_disturbance_y_to_visible()
        self._updating_view -= 1

    def _capture_view_state(self):
        x_range = tuple(float(v) for v in self._view_box.viewRange()[0])
        y_range = tuple(float(v) for v in self._view_box.viewRange()[1])
        return x_range, y_range

    def _states_close(self, left, right):
        lx, ly = left
        rx, ry = right
        return all(abs(a - b) < 1e-6 for a, b in zip(lx + ly, rx + ry))

    def _push_view_history(self, force: bool = False):
        if self._history_navigation:
            return
        state = self._capture_view_state()
        if not force and self._view_history and self._states_close(self._view_history[self._view_history_index], state):
            self._update_history_buttons()
            return
        if self._view_history_index < len(self._view_history) - 1:
            self._view_history = self._view_history[: self._view_history_index + 1]
        self._view_history.append(state)
        if len(self._view_history) > 80:
            self._view_history.pop(0)
        self._view_history_index = len(self._view_history) - 1
        self._update_history_buttons()

    def _restore_view_state(self, state):
        self._history_navigation = True
        self._updating_view += 1
        x_range, y_range = state
        self.plot.setXRange(x_range[0], x_range[1], padding=0.0)
        self.plot.setYRange(y_range[0], y_range[1], padding=0.0)
        self._fit_disturbance_y_to_visible()
        self._updating_view -= 1
        self._history_navigation = False

    def navigate_view_history(self, direction: int):
        if not self._view_history:
            return
        target = self._view_history_index + int(direction)
        if target < 0 or target >= len(self._view_history):
            return
        self._view_history_index = target
        self._set_follow_latest(False)
        self._restore_view_state(self._view_history[self._view_history_index])
        self._update_history_buttons()

    def _update_history_buttons(self):
        can_back = self._view_history_index > 0
        can_forward = 0 <= self._view_history_index < len(self._view_history) - 1
        self.view_back_btn.setEnabled(can_back)
        self.view_forward_btn.setEnabled(can_forward)

    def _toggle_measurement(self, enabled: bool):
        self._measure_line_a.setVisible(enabled)
        self._measure_line_b.setVisible(enabled)
        self.measure_channel_combo.setEnabled(enabled)
        self.capture_a_btn.setEnabled(enabled)
        self.capture_b_btn.setEnabled(enabled)
        self.reset_measure_btn.setEnabled(enabled)
        if enabled:
            self._reset_measurement_lines()
            self._update_measurement_readout()
        else:
            self.measure_label.setText("测量: --")

    def _reset_measurement_lines(self):
        start, end = self._current_x_range()
        span = end - start
        self._measure_line_a.setPos(start + span * 0.25)
        self._measure_line_b.setPos(start + span * 0.75)
        self._update_measurement_readout()

    def _capture_measure_cursor(self, which: str):
        target_x = self._last_mouse_x if self.cursor_cb.isChecked() else self._current_x_range()[0 if which == "a" else 1]
        if which == "a":
            self._measure_line_a.setPos(target_x)
        else:
            self._measure_line_b.setPos(target_x)
        self._update_measurement_readout()

    def _value_at_time(self, channel_name: str, x_value: float):
        channel = self._channels.get(channel_name)
        if channel is None or not channel["x"]:
            return None
        xs = list(channel["x"])
        ys = list(channel["y"])
        idx = bisect_left(xs, x_value)
        if idx <= 0:
            return ys[0]
        if idx >= len(xs):
            return ys[-1]
        x0, x1 = xs[idx - 1], xs[idx]
        y0, y1 = ys[idx - 1], ys[idx]
        if abs(x1 - x0) < 1e-9:
            return y1
        ratio = (x_value - x0) / (x1 - x0)
        return y0 + (y1 - y0) * ratio

    def _update_measurement_readout(self, *args):
        if not self.measurement_cb.isChecked():
            return
        x_a = float(self._measure_line_a.value())
        x_b = float(self._measure_line_b.value())
        channel_name = self.measure_channel_combo.currentData()
        label_text = self.measure_channel_combo.currentText() or "当前通道"
        delta_t = abs(x_b - x_a)
        value_a = self._value_at_time(channel_name, x_a)
        value_b = self._value_at_time(channel_name, x_b)
        if value_a is None or value_b is None:
            self.measure_label.setText(f"测量: Δt={delta_t:.3f}s")
            return
        delta_y = value_b - value_a
        self.measure_label.setText(
            f"测量: Δt={delta_t:.3f}s | {label_text} A={value_a:.3f}, B={value_b:.3f}, Δ={delta_y:.3f}"
        )

    def _collect_visible_y_in_current_x_range(self) -> List[float]:
        x_start, x_end = self._current_x_range()
        values: List[float] = []
        for channel_name, channel in self._channels.items():
            if self._is_disturbance_channel(channel_name):
                continue
            if not channel["visible"] or not channel["x"]:
                continue
            xs = list(channel["x"])
            ys = list(channel["y"])
            scoped = [y for x, y in zip(xs, ys) if x_start <= x <= x_end and math.isfinite(float(y))]
            if not scoped:
                scoped = [y for y in ys if math.isfinite(float(y))]
            values.extend(scoped)
        return values

    def set_channel_visible(self, name: str, visible: bool):
        if name not in self._channels:
            return
        channel = self._channels[name]
        channel["visible"] = visible
        channel["curve"].setVisible(visible)
        if visible:
            self._refresh_channel_curve(name)
        if self._is_disturbance_channel(name):
            self._update_disturbance_axis_visibility()
        self._update_channel_summary()
        self.channel_toggled.emit(name, visible)

    def apply_preset(self, preset_key: str):
        preset = self.PRESET_CHANNELS.get(preset_key)
        if preset is None:
            return
        for channel_name, visible in preset.items():
            if channel_name not in self._channels:
                continue
            self._set_channel_visible_silently(channel_name, visible)
        dynamic_visible = preset_key == "all"
        for channel_name in self._dynamic_algorithm_channels:
            if channel_name not in self._channels:
                continue
            self._set_channel_visible_silently(channel_name, dynamic_visible)
        if preset_key == "balance":
            self._apply_balance_runtime_visibility()
        self._reflow_channel_layout()

    def append(self, t_sec: float, values: Dict[str, float]):
        if self._paused:
            return
        self._latest_time = max(self._latest_time, float(t_sec))
        for name, value in values.items():
            if name not in self._channels:
                self._ensure_dynamic_algorithm_channel(name)
            if name not in self._channels:
                continue
            channel = self._channels[name]
            channel["x"].append(float(t_sec))
            channel["y"].append(float(value))

        self._updating_view += 1
        for channel_name, channel in self._channels.items():
            if channel["visible"]:
                self._refresh_channel_curve(channel_name)

        self._fit_disturbance_y_to_visible()
        if self.follow_latest_cb.isChecked():
            self._apply_latest_window()
        self._updating_view -= 1

    def clear(self):
        self._updating_view += 1
        self.clear_point_markers()
        for channel in self._channels.values():
            channel["x"].clear()
            channel["y"].clear()
            channel["curve"].setData([], [])
        self._latest_time = 0.0
        self.readout_label.setText("游标: --")
        self.measure_label.setText("测量: --")
        self._set_follow_latest(True)
        self._set_default_x_range()
        self._update_disturbance_axis_visibility()
        self._view_history.clear()
        self._view_history_index = -1
        self._push_view_history(force=True)
        self._updating_view -= 1

    def clear_model_series(self):
        self._updating_view += 1
        for channel_name in ("vertical", "vertical_rate", "disturbance_sim", "disturbance_remote", *self._dynamic_algorithm_channels):
            if channel_name not in self._channels:
                continue
            channel = self._channels[channel_name]
            channel["x"].clear()
            channel["y"].clear()
            channel["curve"].setData([], [])
        self._fit_disturbance_y_to_visible()
        if self.follow_latest_cb.isChecked():
            self._apply_latest_window()
        self._updating_view -= 1

    def set_model_context(self, model_type: str):
        vertical_label, vertical_rate_label, disturbance_label = self.MODEL_VERTICAL_LABELS.get(
            model_type,
            self.MODEL_VERTICAL_LABELS["rov"],
        )
        self._rename_channel("vertical", vertical_label)
        self._rename_channel("vertical_rate", vertical_rate_label)
        self._rename_channel("disturbance_sim", disturbance_label)
        self._rename_channel("disturbance_remote", self._channel_display_name("disturbance_remote"))
        self.plot.setLabel("right", disturbance_label, color=self._theme["plot_text"])
        self._apply_algorithm_channel_labels()
        self._populate_measure_channel_combo()
        self._update_measurement_readout()

    def _rename_channel(self, channel_name: str, new_label: str):
        if channel_name not in self._channels:
            return
        channel = self._channels[channel_name]
        control_zh, control_en = self._channel_control_labels(channel_name, new_label)
        checkbox = channel["checkbox"]
        checkbox.setText(control_zh)
        english_label = channel.get("english_label")
        if english_label is not None:
            self._set_english_label_text(english_label, control_en)
        curve = channel["curve"]
        curve.opts["name"] = new_label
        legend = self.plot.plotItem.legend
        if legend is None:
            return
        for sample, label in legend.items:
            if sample.item is curve:
                label.setText(new_label)
                break

    def _apply_algorithm_channel_labels(self):
        for channel_name in self._ordered_channel_names():
            if channel_name not in self.ALGORITHM_CHANNELS and channel_name not in self._dynamic_algorithm_channels:
                continue
            if channel_name not in self._channels:
                continue
            self._rename_channel(channel_name, self._channel_display_name(channel_name))

    def set_algorithm_channel_labels(self, label_map: Dict[str, str] | None):
        normalized: Dict[str, str] = {}
        if isinstance(label_map, dict):
            for key, value in label_map.items():
                channel_name = str(key).strip()
                label = str(value).strip()
                if not channel_name or not label:
                    continue
                if channel_name not in self._channels:
                    self._ensure_dynamic_algorithm_channel(channel_name)
                if channel_name in self._channels:
                    normalized[channel_name] = label
        self._algorithm_channel_labels = normalized
        self._apply_algorithm_channel_labels()
        self._reflow_channel_layout()
        self._populate_measure_channel_combo()
        self._update_measurement_readout()

    def export_plot_image(self):
        default_name = f"wave_{QtCore.QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.png"
        target, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出波形图片",
            str(Path.cwd() / default_name),
            "PNG 图片 (*.png)",
        )
        if not target:
            return
        pixmap = self.plot.grab()
        pixmap.save(target, "PNG")
        self.readout_label.setText(f"已导出图片: {target}")

    def export_visible_csv(self):
        x_start, x_end = self._current_x_range()
        visible_channels = [
            (channel_name, self._channel_display_name(channel_name), channel)
            for channel_name, channel in self._channels.items()
            if channel["visible"]
        ]
        if not visible_channels:
            QtWidgets.QMessageBox.information(self, "提示", "请先至少显示一条波形通道后再导出。")
            return

        timeline_keys = set()
        channel_maps = {}
        for channel_name, _, channel in visible_channels:
            mapping = {}
            for x_value, y_value in zip(channel["x"], channel["y"]):
                if x_start <= x_value <= x_end:
                    key = f"{x_value:.6f}"
                    mapping[key] = y_value
                    timeline_keys.add(key)
            channel_maps[channel_name] = mapping

        if not timeline_keys:
            QtWidgets.QMessageBox.information(self, "提示", "当前时间窗口内没有可导出的波形数据。")
            return

        default_name = f"wave_visible_{QtCore.QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.csv"
        target, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出当前窗口 CSV",
            str(Path.cwd() / default_name),
            "CSV 文件 (*.csv)",
        )
        if not target:
            return

        timeline = sorted(float(key) for key in timeline_keys)
        with open(target, "w", newline="", encoding="utf-8-sig") as fp:
            writer = csv.writer(fp)
            writer.writerow(["time_s"] + [label for _, label, _ in visible_channels])
            for time_value in timeline:
                key = f"{time_value:.6f}"
                row = [f"{time_value:.6f}"]
                for channel_name, _, _ in visible_channels:
                    value = channel_maps[channel_name].get(key, "")
                    row.append("" if value == "" else f"{value:.6f}")
                writer.writerow(row)

        self.readout_label.setText(f"已导出 CSV: {target}")

    def _has_data(self) -> bool:
        return any(channel["x"] for channel in self._channels.values())

    def _time_bounds(self) -> Tuple[float, float]:
        starts = [channel["x"][0] for channel in self._channels.values() if channel["x"]]
        if not starts:
            return 0.0, max(self.window_sec, self._latest_time)
        return min(starts), max(self._latest_time, max(channel["x"][-1] for channel in self._channels.values() if channel["x"]))

    def _current_x_range(self) -> Tuple[float, float]:
        x_range = self._view_box.viewRange()[0]
        return float(x_range[0]), float(x_range[1])

    def _set_default_x_range(self):
        self._apply_time_range(0.0, self.window_sec)

    def _apply_window_around_current_center(self):
        start, end = self._current_x_range()
        center = (start + end) / 2.0
        half = self.window_sec / 2.0
        self._apply_time_range(center - half, center + half)

    def _apply_latest_window(self):
        end = max(self.window_sec, self._latest_time)
        start = max(0.0, end - self.window_sec)
        self._apply_time_range(start, end)

    def _apply_time_range(self, start: float, end: float):
        span = max(self.window_sec, end - start)
        data_min, data_max = self._time_bounds()
        if data_max <= span:
            start = 0.0 if data_min >= 0.0 else data_min
            end = start + span
        else:
            max_start = data_max - span
            start = min(max(start, data_min), max_start)
            end = start + span
        self._updating_view += 1
        self.plot.setXRange(start, end, padding=0.0)
        self._fit_disturbance_y_to_visible()
        self._updating_view -= 1
