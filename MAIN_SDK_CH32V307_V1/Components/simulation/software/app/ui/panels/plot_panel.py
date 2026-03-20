from collections import deque
from typing import Dict, List

from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg


class PlotPanel(QtWidgets.QWidget):
    channel_toggled = QtCore.pyqtSignal(str, bool)

    def __init__(self, window_sec: float = 20.0, parent=None):
        super().__init__(parent)
        self.window_sec = window_sec
        self.max_points = 4000
        self._channels: Dict[str, Dict[str, object]] = {}
        self._build()
        self._init_channels()

    def _build(self):
        root = QtWidgets.QVBoxLayout(self)

        tool = QtWidgets.QHBoxLayout()
        self.pause_btn = QtWidgets.QPushButton("Pause")
        self.clear_btn = QtWidgets.QPushButton("Clear")
        self.window_spin = QtWidgets.QDoubleSpinBox()
        self.window_spin.setRange(5.0, 120.0)
        self.window_spin.setValue(self.window_sec)
        self.window_spin.setSuffix(" s")
        self.window_spin.setSingleStep(5.0)
        tool.addWidget(self.pause_btn)
        tool.addWidget(self.clear_btn)
        tool.addWidget(QtWidgets.QLabel("Window"))
        tool.addWidget(self.window_spin)
        tool.addStretch(1)
        root.addLayout(tool)

        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.plot.addLegend(colCount=2)
        self.plot.setLabel("bottom", "Time", units="s")
        self.plot.setLabel("left", "Value")
        self.plot.setBackground("#0f172a")
        root.addWidget(self.plot, 1)

        self.channel_box = QtWidgets.QGroupBox("Channels")
        self.channel_layout = QtWidgets.QHBoxLayout(self.channel_box)
        root.addWidget(self.channel_box)

        self.pause_btn.clicked.connect(self._toggle_pause)
        self.clear_btn.clicked.connect(self.clear)
        self.window_spin.valueChanged.connect(self._set_window_sec)
        self._paused = False

    def _init_channels(self):
        specs = [
            ("ref", "#38bdf8"),
            ("feedback", "#22c55e"),
            ("u_cmd", "#f97316"),
            ("roll", "#eab308"),
            ("pitch", "#a78bfa"),
            ("yaw", "#f43f5e"),
            ("depth_rate", "#14b8a6"),
            ("disturbance", "#94a3b8"),
        ]
        for idx, (name, color) in enumerate(specs):
            checked = idx < 5
            self._add_channel(name, color, checked)

    def _add_channel(self, name: str, color: str, checked: bool):
        curve = self.plot.plot([], [], pen=pg.mkPen(color=color, width=1.8), name=name)
        curve.setVisible(checked)
        cb = QtWidgets.QCheckBox(name)
        cb.setChecked(checked)
        cb.toggled.connect(lambda on, ch=name: self.set_channel_visible(ch, on))
        self.channel_layout.addWidget(cb)
        self._channels[name] = {
            "curve": curve,
            "x": deque(maxlen=self.max_points),
            "y": deque(maxlen=self.max_points),
            "visible": checked,
            "checkbox": cb,
        }

    def _toggle_pause(self):
        self._paused = not self._paused
        self.pause_btn.setText("Resume" if self._paused else "Pause")

    def _set_window_sec(self, value: float):
        self.window_sec = value

    def set_channel_visible(self, name: str, visible: bool):
        if name not in self._channels:
            return
        ch = self._channels[name]
        ch["visible"] = visible
        ch["curve"].setVisible(visible)
        self.channel_toggled.emit(name, visible)

    def append(self, t_sec: float, values: Dict[str, float]):
        if self._paused:
            return
        for name, val in values.items():
            if name not in self._channels:
                continue
            ch = self._channels[name]
            ch["x"].append(t_sec)
            ch["y"].append(float(val))

        x_min = t_sec - self.window_sec
        for ch in self._channels.values():
            xs: deque = ch["x"]
            ys: deque = ch["y"]
            while xs and xs[0] < x_min:
                xs.popleft()
                ys.popleft()
            if ch["visible"]:
                ch["curve"].setData(list(xs), list(ys))

        self.plot.setXRange(max(0.0, x_min), max(self.window_sec, t_sec), padding=0.01)

    def clear(self):
        for ch in self._channels.values():
            ch["x"].clear()
            ch["y"].clear()
            ch["curve"].setData([], [])

