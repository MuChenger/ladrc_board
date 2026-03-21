from PyQt5 import QtCore, QtWidgets


class CommandPanel(QtWidgets.QGroupBox):
    ALGORITHM_OPTIONS = [
        ("PID", "PID"),
        ("LADRC", "LADRC"),
        ("开环", "OPEN_LOOP"),
    ]

    send_command = QtCore.pyqtSignal(str)
    algo_selected = QtCore.pyqtSignal(str)
    ref_changed = QtCore.pyqtSignal(float)
    console_message = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("基础控制", parent)
        self._history = []
        self._history_idx = -1
        self._build()
        self._apply_size_hints()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        row0 = QtWidgets.QHBoxLayout()
        row0.setSpacing(8)
        self.algo_combo = QtWidgets.QComboBox()
        self.algo_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        for label, value in self.ALGORITHM_OPTIONS:
            self.algo_combo.addItem(label, value)
        self.apply_algo_btn = QtWidgets.QPushButton("应用算法")
        row0.addWidget(QtWidgets.QLabel("算法"))
        row0.addWidget(self.algo_combo, 1)
        row0.addWidget(self.apply_algo_btn)

        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(8)
        self.ref_spin = QtWidgets.QDoubleSpinBox()
        self.ref_spin.setRange(-1000.0, 1000.0)
        self.ref_spin.setDecimals(3)
        self.ref_spin.setSingleStep(0.1)
        self.set_ref_btn = QtWidgets.QPushButton("设置参考值")
        self.run_btn = QtWidgets.QPushButton("启动")
        self.stop_btn = QtWidgets.QPushButton("停止")
        row1.addWidget(QtWidgets.QLabel("参考值"))
        row1.addWidget(self.ref_spin, 1)
        row1.addWidget(self.set_ref_btn)
        row1.addWidget(self.run_btn)
        row1.addWidget(self.stop_btn)

        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(8)
        self.command_edit = QtWidgets.QLineEdit()
        self.command_edit.setPlaceholderText("输入命令，例如：SET KP 1.2")
        self.send_btn = QtWidgets.QPushButton("发送")
        self.status_btn = QtWidgets.QPushButton("读取状态")
        row2.addWidget(self.command_edit, 1)
        row2.addWidget(self.send_btn)
        row2.addWidget(self.status_btn)

        layout.addLayout(row0)
        layout.addLayout(row1)
        layout.addLayout(row2)

        self.apply_algo_btn.clicked.connect(self._send_alg)
        self.set_ref_btn.clicked.connect(self._send_ref)
        self.run_btn.clicked.connect(lambda: self._send_direct("RUN 1"))
        self.stop_btn.clicked.connect(lambda: self._send_direct("RUN 0"))
        self.send_btn.clicked.connect(self._send_from_edit)
        self.status_btn.clicked.connect(lambda: self._send_direct("GET STATUS"))
        self.command_edit.returnPressed.connect(self._send_from_edit)

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
