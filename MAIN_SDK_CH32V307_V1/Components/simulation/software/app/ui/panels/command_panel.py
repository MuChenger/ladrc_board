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

    def set_disturbance_level(self, level_key: str):
        for index in range(self.disturbance_combo.count()):
            data = self.disturbance_combo.itemData(index)
            if data and data[0] == level_key:
                self.disturbance_combo.setCurrentIndex(index)
                return

    def get_state(self) -> dict:
        return {
            "algorithm": self.algo_combo.currentData(),
            "reference": float(self.ref_spin.value()),
            "command_text": self.command_edit.text(),
            "disturbance_level": self.current_disturbance_key(),
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

    def reset_to_defaults(self):
        self.algo_combo.setCurrentIndex(0)
        self.ref_spin.setValue(0.0)
        self.command_edit.clear()
        self.set_disturbance_level("medium")
