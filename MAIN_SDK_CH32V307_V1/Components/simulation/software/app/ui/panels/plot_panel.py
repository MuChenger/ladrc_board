from collections import deque
from typing import Dict

from PyQt5 import QtCore, QtWidgets
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

    def __init__(self, window_sec: float = 20.0, parent=None):
        super().__init__(parent)
        self.window_sec = window_sec
        self.max_points = 4000
        self._paused = False
        self._channels: Dict[str, Dict[str, object]] = {}
        self._channel_widget_detached = False
        self._build()
        self._init_channels()
        self.apply_preset(self.preset_combo.currentData())

    def _build(self):
        self._root_layout = QtWidgets.QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(10)

        tool = QtWidgets.QHBoxLayout()
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
        tool.addWidget(self.pause_btn)
        tool.addWidget(self.clear_btn)
        tool.addWidget(QtWidgets.QLabel("预设"))
        tool.addWidget(self.preset_combo)
        tool.addWidget(QtWidgets.QLabel("时间窗口"))
        tool.addWidget(self.window_spin)
        tool.addStretch(1)
        self._root_layout.addLayout(tool)

        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.22)
        self.plot.addLegend(colCount=2)
        self.plot.setLabel("bottom", "时间", units="s")
        self.plot.setLabel("left", "数值")
        self.plot.setBackground("#0f172a")
        self._root_layout.addWidget(self.plot, 1)

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
        row = index // 2
        column = index % 2
        self.channel_layout.addWidget(checkbox, row, column)
        self._channels[name] = {
            "curve": curve,
            "x": deque(maxlen=self.max_points),
            "y": deque(maxlen=self.max_points),
            "visible": checked,
            "checkbox": checkbox,
        }

    def take_channel_widget(self) -> QtWidgets.QWidget:
        if not self._channel_widget_detached:
            self._root_layout.removeWidget(self.channel_box)
            self.channel_box.setParent(None)
            self._channel_widget_detached = True
        return self.channel_box

    def _toggle_pause(self):
        self._paused = not self._paused
        self.pause_btn.setText("继续" if self._paused else "暂停")

    def _set_window_sec(self, value: float):
        self.window_sec = value

    def _apply_selected_preset(self):
        preset_key = self.preset_combo.currentData()
        if preset_key:
            self.apply_preset(preset_key)

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
        for name, value in values.items():
            if name not in self._channels:
                continue
            channel = self._channels[name]
            channel["x"].append(t_sec)
            channel["y"].append(float(value))

        x_min = t_sec - self.window_sec
        for channel in self._channels.values():
            xs = channel["x"]
            ys = channel["y"]
            while xs and xs[0] < x_min:
                xs.popleft()
                ys.popleft()
            if channel["visible"]:
                channel["curve"].setData(list(xs), list(ys))

        self.plot.setXRange(max(0.0, x_min), max(self.window_sec, t_sec), padding=0.01)

    def clear(self):
        for channel in self._channels.values():
            channel["x"].clear()
            channel["y"].clear()
            channel["curve"].setData([], [])

    def clear_model_series(self):
        for channel_name in ("vertical", "vertical_rate", "disturbance"):
            if channel_name not in self._channels:
                continue
            channel = self._channels[channel_name]
            channel["x"].clear()
            channel["y"].clear()
            channel["curve"].setData([], [])

    def set_model_context(self, model_type: str):
        vertical_label, vertical_rate_label, disturbance_label = self.MODEL_VERTICAL_LABELS.get(
            model_type,
            self.MODEL_VERTICAL_LABELS["rov"],
        )
        self._rename_channel("vertical", vertical_label)
        self._rename_channel("vertical_rate", vertical_rate_label)
        self._rename_channel("disturbance", disturbance_label)

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
