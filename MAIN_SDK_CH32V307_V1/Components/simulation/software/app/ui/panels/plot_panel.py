import csv
from bisect import bisect_left
from collections import deque
from pathlib import Path
from typing import Dict, List, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg


class PlotPanel(QtWidgets.QWidget):
    channel_toggled = QtCore.pyqtSignal(str, bool)

    CHANNEL_LABELS = {
        "ref": "参考值",
        "feedback": "控制反馈",
        "u_cmd": "控制输出",
        "roll": "滚转角",
        "pitch": "俯仰角",
        "yaw": "偏航角",
        "vertical": "垂向量",
        "vertical_rate": "垂向速度",
        "disturbance": "外部扰动",
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
            "u_cmd": True,
            "roll": True,
            "pitch": True,
            "yaw": False,
            "vertical": True,
            "vertical_rate": False,
            "disturbance": False,
        },
        "attitude": {
            "ref": True,
            "feedback": True,
            "u_cmd": True,
            "roll": True,
            "pitch": True,
            "yaw": True,
            "vertical": False,
            "vertical_rate": False,
            "disturbance": False,
        },
        "vertical": {
            "ref": True,
            "feedback": True,
            "u_cmd": True,
            "roll": False,
            "pitch": False,
            "yaw": False,
            "vertical": True,
            "vertical_rate": True,
            "disturbance": True,
        },
        "all": {
            "ref": True,
            "feedback": True,
            "u_cmd": True,
            "roll": True,
            "pitch": True,
            "yaw": True,
            "vertical": True,
            "vertical_rate": True,
            "disturbance": True,
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
        self._updating_view = False
        self._history_navigation = False
        self._view_history: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        self._view_history_index = -1
        self._last_mouse_x = 0.0
        self._point_markers = []
        self._theme = self._default_theme()
        self._build()
        self._init_channels()
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
        self._root_layout.setSpacing(10)

        tool_widget = QtWidgets.QWidget()
        tool_layout = QtWidgets.QVBoxLayout(tool_widget)
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.setSpacing(4)

        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(8)
        self.pause_btn = QtWidgets.QPushButton("暂停")
        self.clear_btn = QtWidgets.QPushButton("清空")
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItem("平衡视图", "balance")
        self.preset_combo.addItem("姿态调试", "attitude")
        self.preset_combo.addItem("垂向控制", "vertical")
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
        self.annotation_cb = QtWidgets.QCheckBox("点击标记")
        self.readout_label = QtWidgets.QLabel("游标: --")
        self.readout_label.setObjectName("statusHint")
        self.readout_label.setMinimumWidth(160)
        self.readout_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.measure_label = QtWidgets.QLabel("测量: --")
        self.measure_label.setObjectName("statusHint")
        self.measure_label.setMinimumWidth(160)
        self.measure_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        row1.addWidget(self.pause_btn)
        row1.addWidget(self.clear_btn)
        row1.addWidget(QtWidgets.QLabel("预设"))
        row1.addWidget(self.preset_combo)
        row1.addWidget(QtWidgets.QLabel("时间窗口"))
        row1.addWidget(self.window_spin)
        row1.addWidget(self.follow_latest_cb)
        row1.addWidget(self.focus_btn)
        row1.addWidget(self.annotation_cb)
        row1.addStretch(1)
        row1.addWidget(self.readout_label, 1)
        row1.addWidget(self.measure_label, 1)
        tool_layout.addLayout(row1)
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
        self._root_layout.addWidget(tool_widget)

        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.22)
        self.plot.addLegend(colCount=2)
        self.plot.setLabel("bottom", "时间", units="s")
        self.plot.setLabel("left", "数值")
        self.plot.setBackground("#0f172a")
        self.plot.setClipToView(True)
        self._root_layout.addWidget(self.plot, 1)

        self._view_box = self.plot.getViewBox()
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

        self.channel_box = QtWidgets.QGroupBox("波形通道")
        self.channel_layout = QtWidgets.QGridLayout(self.channel_box)
        self.channel_layout.setContentsMargins(12, 12, 12, 12)
        self.channel_layout.setHorizontalSpacing(14)
        self.channel_layout.setVerticalSpacing(8)
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
        self.annotation_cb.setToolTip("开启后，点击波形可在最近数据点添加标签")
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
            ("ref", "#38bdf8", True),
            ("feedback", "#22c55e", True),
            ("u_cmd", "#f97316", True),
            ("roll", "#eab308", True),
            ("pitch", "#a78bfa", True),
            ("yaw", "#f43f5e", False),
            ("vertical", "#14b8a6", True),
            ("vertical_rate", "#0ea5e9", False),
            ("disturbance", "#94a3b8", False),
        ]
        for name, color, checked in specs:
            self._add_channel(name, color, checked)

    def _add_channel(self, name: str, color: str, checked: bool):
        display_name = self.CHANNEL_LABELS.get(name, name)
        curve = self.plot.plot([], [], pen=pg.mkPen(color=color, width=1.8), name=display_name)
        curve.setVisible(checked)
        checkbox = QtWidgets.QCheckBox(display_name)
        checkbox.setChecked(checked)
        checkbox.toggled.connect(lambda on, ch=name: self.set_channel_visible(ch, on))
        index = len(self._channels)
        self.channel_layout.addWidget(checkbox, index, 0)
        self._channels[name] = {
            "curve": curve,
            "x": deque(maxlen=self.max_points),
            "y": deque(maxlen=self.max_points),
            "visible": checked,
            "checkbox": checkbox,
        }

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
        for channel_name, channel in self._channels.items():
            self.measure_channel_combo.addItem(channel["checkbox"].text(), channel_name)
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
                checkbox = self._channels[channel_name]["checkbox"]
                blocker = QtCore.QSignalBlocker(checkbox)
                checkbox.setChecked(bool(visible))
                del blocker
                self.set_channel_visible(channel_name, bool(visible))

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
        for axis_name in ("left", "bottom"):
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
            marker_info["marker"].setPen(pg.mkPen(self._to_qcolor(self._theme["plot_annotation_border"]), width=1.1))
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
            "padding: 6px 8px; border: 1px solid {border}; border-radius: 4px;'>"
            "<b>{label}</b><br/>t={x:.3f}s<br/>值={y:.3f}</div>"
        ).format(
            bg=self._theme["plot_annotation_bg"],
            fg=self._theme["plot_annotation_text"],
            border=self._theme["plot_annotation_border"],
            label=label_text,
            x=x_value,
            y=y_value,
        )

    def _set_window_sec(self, value: float):
        self._push_view_history()
        self.window_sec = float(value)
        if self.follow_latest_cb.isChecked():
            self._apply_latest_window()
        else:
            self._apply_window_around_current_center()
        self._push_view_history()

    def _apply_selected_preset(self):
        preset_key = self.preset_combo.currentData()
        if preset_key:
            self.apply_preset(preset_key)

    def _on_follow_latest_changed(self, checked: bool):
        if checked:
            self._apply_latest_window()

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
        if not self.cursor_cb.isChecked():
            return
        pos = event[0] if isinstance(event, tuple) else event
        if not self.plot.plotItem.sceneBoundingRect().contains(pos):
            return
        mouse_point = self._view_box.mapSceneToView(pos)
        x_value = mouse_point.x()
        y_value = mouse_point.y()
        self._last_mouse_x = float(x_value)
        self._cursor_v_line.setPos(x_value)
        self._cursor_h_line.setPos(y_value)
        extras = self._nearest_visible_values(x_value)
        suffix = f" | {' | '.join(extras)}" if extras else ""
        self.readout_label.setText(f"游标: t={x_value:.2f}s, y={y_value:.3f}{suffix}")

    def _on_plot_clicked(self, event):
        if not self.annotation_cb.isChecked():
            return
        if event.button() != QtCore.Qt.LeftButton:
            return
        pos = event.scenePos()
        if not self.plot.plotItem.sceneBoundingRect().contains(pos):
            return
        mouse_point = self._view_box.mapSceneToView(pos)
        marker = self._find_nearest_visible_point(mouse_point.x(), mouse_point.y())
        if marker is None:
            return
        self._add_point_marker(*marker)
        event.accept()

    def _find_nearest_visible_point(self, x_value: float, y_value: float):
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
            score = abs(px - x_value) * 0.7 + abs(py - y_value) * 0.3
            if best_score is None or score < best_score:
                best_score = score
                best = (channel_name, channel["checkbox"].text(), float(px), float(py))
        return best

    def _add_point_marker(self, channel_name: str, label_text: str, x_value: float, y_value: float):
        marker = pg.ScatterPlotItem(
            x=[x_value],
            y=[y_value],
            symbol="o",
            size=9,
            pen=pg.mkPen(self._to_qcolor(self._theme["plot_annotation_border"]), width=1.1),
            brush=pg.mkBrush(self._theme["plot_measure_a"]),
        )
        self.plot.addItem(marker)

        text_item = pg.TextItem(
            html=self._build_annotation_html(label_text, x_value, y_value),
            anchor=(0, 1),
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
            label = channel["checkbox"].text()
            parts.append(f"{label}={ys[nearest_index]:.3f}")
            if len(parts) >= 2:
                break
        return parts

    def _on_manual_range_changed(self, *args):
        if self._updating_view:
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
        self._push_view_history()
        step = self.window_sec * factor
        self._set_follow_latest(False)
        start, end = self._current_x_range()
        self._apply_time_range(start + step, end + step)
        self._push_view_history()

    def _set_follow_latest(self, enabled: bool):
        blocker = QtCore.QSignalBlocker(self.follow_latest_cb)
        self.follow_latest_cb.setChecked(enabled)
        del blocker

    def focus_latest(self):
        self._push_view_history()
        self._set_follow_latest(True)
        self._apply_latest_window()
        self._push_view_history()

    def focus_current_view(self):
        self.focus_latest()
        self.fit_y_to_visible()

    def fit_y_to_visible(self):
        y_values = self._collect_visible_y_in_current_x_range()
        if not y_values:
            return
        self._push_view_history()
        y_min = min(y_values)
        y_max = max(y_values)
        if abs(y_max - y_min) < 1e-6:
            pad = max(0.5, abs(y_max) * 0.1 + 0.5)
            y_min -= pad
            y_max += pad
        else:
            pad = (y_max - y_min) * 0.12
            y_min -= pad
            y_max += pad
        self._updating_view = True
        self.plot.setYRange(y_min, y_max, padding=0.0)
        self._updating_view = False
        self._push_view_history()

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
        self._updating_view = True
        x_range, y_range = state
        self.plot.setXRange(x_range[0], x_range[1], padding=0.0)
        self.plot.setYRange(y_range[0], y_range[1], padding=0.0)
        self._updating_view = False
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
        for channel in self._channels.values():
            if not channel["visible"] or not channel["x"]:
                continue
            xs = list(channel["x"])
            ys = list(channel["y"])
            scoped = [y for x, y in zip(xs, ys) if x_start <= x <= x_end]
            if not scoped:
                scoped = ys
            values.extend(scoped)
        return values

    def set_channel_visible(self, name: str, visible: bool):
        if name not in self._channels:
            return
        channel = self._channels[name]
        channel["visible"] = visible
        channel["curve"].setVisible(visible)
        if visible:
            channel["curve"].setData(list(channel["x"]), list(channel["y"]))
        self.channel_toggled.emit(name, visible)

    def apply_preset(self, preset_key: str):
        preset = self.PRESET_CHANNELS.get(preset_key)
        if preset is None:
            return
        for channel_name, visible in preset.items():
            if channel_name not in self._channels:
                continue
            checkbox = self._channels[channel_name]["checkbox"]
            blocker = QtCore.QSignalBlocker(checkbox)
            checkbox.setChecked(visible)
            del blocker
            self.set_channel_visible(channel_name, visible)

    def append(self, t_sec: float, values: Dict[str, float]):
        if self._paused:
            return
        self._latest_time = max(self._latest_time, float(t_sec))
        for name, value in values.items():
            if name not in self._channels:
                continue
            channel = self._channels[name]
            channel["x"].append(float(t_sec))
            channel["y"].append(float(value))

        for channel in self._channels.values():
            if channel["visible"]:
                channel["curve"].setData(list(channel["x"]), list(channel["y"]))

        if self.follow_latest_cb.isChecked():
            self._apply_latest_window()

    def clear(self):
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
        self._view_history.clear()
        self._view_history_index = -1
        self._push_view_history(force=True)

    def clear_model_series(self):
        for channel_name in ("vertical", "vertical_rate", "disturbance"):
            if channel_name not in self._channels:
                continue
            channel = self._channels[channel_name]
            channel["x"].clear()
            channel["y"].clear()
            channel["curve"].setData([], [])
        if self.follow_latest_cb.isChecked():
            self._apply_latest_window()

    def set_model_context(self, model_type: str):
        vertical_label, vertical_rate_label, disturbance_label = self.MODEL_VERTICAL_LABELS.get(
            model_type,
            self.MODEL_VERTICAL_LABELS["rov"],
        )
        self._rename_channel("vertical", vertical_label)
        self._rename_channel("vertical_rate", vertical_rate_label)
        self._rename_channel("disturbance", disturbance_label)
        self._populate_measure_channel_combo()
        self._update_measurement_readout()

    def _rename_channel(self, channel_name: str, new_label: str):
        if channel_name not in self._channels:
            return
        channel = self._channels[channel_name]
        checkbox = channel["checkbox"]
        checkbox.setText(new_label)
        curve = channel["curve"]
        curve.opts["name"] = new_label
        legend = self.plot.plotItem.legend
        if legend is None:
            return
        for sample, label in legend.items:
            if sample.item is curve:
                label.setText(new_label)
                break

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
            (channel_name, channel["checkbox"].text(), channel)
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
        self._updating_view = True
        self.plot.setXRange(start, end, padding=0.0)
        self._updating_view = False
