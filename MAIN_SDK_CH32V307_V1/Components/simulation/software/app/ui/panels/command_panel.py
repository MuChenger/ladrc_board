from typing import Optional

from PyQt5 import QtCore, QtWidgets


class CommandPanel(QtWidgets.QGroupBox):
    ALGORITHM_OPTIONS = [
        ("PID", "PID"),
        ("LADRC", "LADRC"),
        ("开环", "OPEN_LOOP"),
    ]
    DISTURBANCE_LEVELS = [
        ("关闭", "off", 0.0),
        ("低", "low", 0.5),
        ("中", "medium", 1.0),
        ("高", "high", 1.6),
        ("极高", "extreme", 2.4),
    ]

    send_command = QtCore.pyqtSignal(str)
    algo_selected = QtCore.pyqtSignal(str)
    ref_changed = QtCore.pyqtSignal(float)
    disturbance_level_changed = QtCore.pyqtSignal(str, float)
    sim_period_changed = QtCore.pyqtSignal(int)
    simulated_upload_changed = QtCore.pyqtSignal(bool)
    console_message = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("基础控制", parent)
        self._history = []
        self._history_idx = -1
        self._build()
        self._apply_size_hints()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        algo_caption = QtWidgets.QLabel("算法切换")
        algo_caption.setObjectName("statusHint")

        algo_row = QtWidgets.QHBoxLayout()
        algo_row.setSpacing(8)
        self.algo_combo = QtWidgets.QComboBox()
        self.algo_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        for label, value in self.ALGORITHM_OPTIONS:
            self.algo_combo.addItem(label, value)
        self.apply_algo_btn = QtWidgets.QPushButton("应用算法")
        algo_row.addWidget(self.algo_combo, 1)
        algo_row.addWidget(self.apply_algo_btn)

        ref_caption = QtWidgets.QLabel("参考值设置")
        ref_caption.setObjectName("statusHint")

        ref_row = QtWidgets.QHBoxLayout()
        ref_row.setSpacing(8)
        self.ref_spin = QtWidgets.QDoubleSpinBox()
        self.ref_spin.setRange(-1000.0, 1000.0)
        self.ref_spin.setDecimals(3)
        self.ref_spin.setSingleStep(0.1)
        self.set_ref_btn = QtWidgets.QPushButton("设置参考值")
        ref_row.addWidget(self.ref_spin, 1)
        ref_row.addWidget(self.set_ref_btn)

        disturbance_caption = QtWidgets.QLabel("环境扰动")
        disturbance_caption.setObjectName("statusHint")

        disturbance_row = QtWidgets.QHBoxLayout()
        disturbance_row.setSpacing(8)
        self.disturbance_combo = QtWidgets.QComboBox()
        self.disturbance_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        for label, key, scale in self.DISTURBANCE_LEVELS:
            self.disturbance_combo.addItem(label, (key, scale))
        self.set_disturbance_level("medium")
        disturbance_row.addWidget(QtWidgets.QLabel("扰动等级"))
        disturbance_row.addWidget(self.disturbance_combo, 1)

        sim_caption = QtWidgets.QLabel("仿真运行")
        sim_caption.setObjectName("statusHint")

        sim_row = QtWidgets.QHBoxLayout()
        sim_row.setSpacing(8)
        sim_row.addWidget(QtWidgets.QLabel("运行周期"))
        self.sim_period_spin = QtWidgets.QSpinBox()
        self.sim_period_spin.setRange(5, 1000)
        self.sim_period_spin.setSingleStep(5)
        self.sim_period_spin.setSuffix(" ms")
        self.sim_period_spin.setKeyboardTracking(False)
        self.sim_period_spin.setToolTip("设置上位机本地仿真的运行周期，数值越小更新越快。")
        self.sim_rate_label = QtWidgets.QLabel()
        self.sim_rate_label.setObjectName("statusHint")
        sim_row.addWidget(self.sim_period_spin)
        sim_row.addWidget(self.sim_rate_label)
        sim_row.addStretch(1)
        self.set_sim_period_ms(10, emit_signal=False)

        upload_row = QtWidgets.QHBoxLayout()
        upload_row.setSpacing(8)
        self.simulated_upload_cb = QtWidgets.QCheckBox("模拟下位机上传（免串口体验）")
        self.simulated_upload_cb.setToolTip("启用后，在未连接串口时由上位机本地生成下位机遥测，便于直接体验波形、状态与 3D 联动。")
        upload_row.addWidget(self.simulated_upload_cb)
        upload_row.addStretch(1)

        action_row = QtWidgets.QHBoxLayout()
        action_row.setSpacing(8)
        self.run_btn = QtWidgets.QPushButton("启动")
        self.stop_btn = QtWidgets.QPushButton("停止")
        self.status_btn = QtWidgets.QPushButton("读取状态")
        action_row.addWidget(self.run_btn)
        action_row.addWidget(self.stop_btn)
        action_row.addWidget(self.status_btn)

        command_caption = QtWidgets.QLabel("自定义命令")
        command_caption.setObjectName("statusHint")

        self.command_edit = QtWidgets.QLineEdit()
        self.command_edit.setPlaceholderText("输入命令，例如：SET KP 1.2")

        send_row = QtWidgets.QHBoxLayout()
        send_row.setContentsMargins(0, 0, 0, 0)
        self.send_btn = QtWidgets.QPushButton("发送")
        send_row.addStretch(1)
        send_row.addWidget(self.send_btn)

        layout.addWidget(algo_caption)
        layout.addLayout(algo_row)
        layout.addWidget(ref_caption)
        layout.addLayout(ref_row)
        layout.addWidget(disturbance_caption)
        layout.addLayout(disturbance_row)
        layout.addWidget(sim_caption)
        layout.addLayout(sim_row)
        layout.addLayout(upload_row)
        layout.addLayout(action_row)
        layout.addWidget(command_caption)
        layout.addWidget(self.command_edit)
        layout.addLayout(send_row)

        self.apply_algo_btn.clicked.connect(self._send_alg)
        self.set_ref_btn.clicked.connect(self._send_ref)
        self.run_btn.clicked.connect(lambda: self._send_direct("RUN 1"))
        self.stop_btn.clicked.connect(lambda: self._send_direct("RUN 0"))
        self.send_btn.clicked.connect(self._send_from_edit)
        self.status_btn.clicked.connect(lambda: self._send_direct("GET STATUS"))
        self.command_edit.returnPressed.connect(self._send_from_edit)
        self.disturbance_combo.currentIndexChanged.connect(self._emit_disturbance_level)
        self.sim_period_spin.valueChanged.connect(self._on_sim_period_changed)
        self.simulated_upload_cb.toggled.connect(self.simulated_upload_changed.emit)

    def _apply_size_hints(self):
        metrics = self.fontMetrics()
        for button in (
            self.apply_algo_btn,
            self.set_ref_btn,
            self.run_btn,
            self.stop_btn,
            self.send_btn,
            self.status_btn,
        ):
            button.setMinimumWidth(metrics.horizontalAdvance(button.text()) + 28)

    def _send_alg(self):
        algo = self.algo_combo.currentData()
        self.algo_selected.emit(algo)
        self._send_direct(f"ALG {algo}")

    def _send_ref(self):
        value = self.ref_spin.value()
        self.ref_changed.emit(value)
        self._send_direct(f"SET REF {value:.3f}")

    def _send_direct(self, command: str):
        self.send_command.emit(command)
        self.append_console(f"> {command}")

    def _emit_disturbance_level(self):
        self.disturbance_level_changed.emit(self.current_disturbance_key(), self.current_disturbance_scale())

    def _on_sim_period_changed(self, value: int):
        self._refresh_sim_rate_label(int(value))
        self.sim_period_changed.emit(int(value))

    def _send_from_edit(self):
        command = self.command_edit.text().strip()
        if not command:
            return
        self._history.append(command)
        self._history_idx = len(self._history)
        self._send_direct(command)
        self.command_edit.clear()

    def append_console(self, line: str):
        self.console_message.emit(line)

    def current_disturbance_key(self) -> str:
        data = self.disturbance_combo.currentData()
        return data[0] if data else "medium"

    def current_disturbance_scale(self) -> float:
        data = self.disturbance_combo.currentData()
        return float(data[1]) if data else 1.0

    def current_disturbance_label(self) -> str:
        return self.disturbance_combo.currentText()

    def current_sim_period_ms(self) -> int:
        return int(self.sim_period_spin.value())

    def is_simulated_upload_enabled(self) -> bool:
        return self.simulated_upload_cb.isChecked()

    def set_disturbance_level(self, level_key: str):
        for index in range(self.disturbance_combo.count()):
            data = self.disturbance_combo.itemData(index)
            if data and data[0] == level_key:
                self.disturbance_combo.setCurrentIndex(index)
                return

    def set_sim_period_ms(self, period_ms: int, emit_signal: bool = True):
        period_ms = max(self.sim_period_spin.minimum(), min(self.sim_period_spin.maximum(), int(period_ms)))
        blocker = QtCore.QSignalBlocker(self.sim_period_spin)
        self.sim_period_spin.setValue(period_ms)
        del blocker
        self._refresh_sim_rate_label(period_ms)
        if emit_signal:
            self.sim_period_changed.emit(period_ms)

    def set_simulated_upload_enabled(self, enabled: bool, emit_signal: bool = True):
        blocker = QtCore.QSignalBlocker(self.simulated_upload_cb)
        self.simulated_upload_cb.setChecked(bool(enabled))
        del blocker
        if emit_signal:
            self.simulated_upload_changed.emit(bool(enabled))

    def _refresh_sim_rate_label(self, period_ms: Optional[int] = None):
        period_ms = int(period_ms if period_ms is not None else self.sim_period_spin.value())
        hz = 1000.0 / max(1, period_ms)
        self.sim_rate_label.setText(f"约 {hz:.1f} Hz")

    def get_state(self) -> dict:
        return {
            "algorithm": self.algo_combo.currentData(),
            "reference": float(self.ref_spin.value()),
            "command_text": self.command_edit.text(),
            "disturbance_level": self.current_disturbance_key(),
            "sim_period_ms": self.current_sim_period_ms(),
            "simulated_upload": self.is_simulated_upload_enabled(),
        }

    def apply_state(self, state: dict):
        if not isinstance(state, dict):
            return
        algo = state.get("algorithm")
        if algo is not None:
            index = self.algo_combo.findData(algo)
            if index >= 0:
                self.algo_combo.setCurrentIndex(index)
        if "reference" in state:
            try:
                self.ref_spin.setValue(float(state.get("reference", 0.0)))
            except (TypeError, ValueError):
                pass
        if "command_text" in state:
            self.command_edit.setText(str(state.get("command_text", "")))
        if "disturbance_level" in state:
            self.set_disturbance_level(str(state.get("disturbance_level", "medium")))
        if "sim_period_ms" in state:
            try:
                self.set_sim_period_ms(int(state.get("sim_period_ms", 10)), emit_signal=False)
            except (TypeError, ValueError):
                self.set_sim_period_ms(10, emit_signal=False)
        if "simulated_upload" in state:
            self.set_simulated_upload_enabled(bool(state.get("simulated_upload")), emit_signal=True)

    def reset_to_defaults(self):
        self.algo_combo.setCurrentIndex(0)
        self.ref_spin.setValue(0.0)
        self.command_edit.clear()
        self.set_disturbance_level("medium")
        self.set_sim_period_ms(10)
        self.set_simulated_upload_enabled(False)
