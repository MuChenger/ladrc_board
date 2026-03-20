from PyQt5 import QtCore, QtWidgets


class CommandPanel(QtWidgets.QGroupBox):
    send_command = QtCore.pyqtSignal(str)
    run_toggle = QtCore.pyqtSignal(bool)
    algo_selected = QtCore.pyqtSignal(str)
    ref_changed = QtCore.pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__("Control Console", parent)
        self._history = []
        self._history_idx = -1
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)

        row0 = QtWidgets.QHBoxLayout()
        self.algo_combo = QtWidgets.QComboBox()
        self.algo_combo.addItems(["PID", "LADRC", "OPEN_LOOP"])
        self.apply_algo_btn = QtWidgets.QPushButton("Apply ALG")
        row0.addWidget(QtWidgets.QLabel("Algorithm"))
        row0.addWidget(self.algo_combo)
        row0.addWidget(self.apply_algo_btn)

        row1 = QtWidgets.QHBoxLayout()
        self.ref_spin = QtWidgets.QDoubleSpinBox()
        self.ref_spin.setRange(-1000.0, 1000.0)
        self.ref_spin.setDecimals(3)
        self.ref_spin.setSingleStep(0.1)
        self.set_ref_btn = QtWidgets.QPushButton("SET REF")
        self.run_btn = QtWidgets.QPushButton("RUN 1")
        self.stop_btn = QtWidgets.QPushButton("RUN 0")
        row1.addWidget(QtWidgets.QLabel("Ref"))
        row1.addWidget(self.ref_spin)
        row1.addWidget(self.set_ref_btn)
        row1.addWidget(self.run_btn)
        row1.addWidget(self.stop_btn)

        row2 = QtWidgets.QHBoxLayout()
        self.command_edit = QtWidgets.QLineEdit()
        self.command_edit.setPlaceholderText("Input command, e.g. SET KP 1.2")
        self.send_btn = QtWidgets.QPushButton("Send")
        self.status_btn = QtWidgets.QPushButton("GET STATUS")
        row2.addWidget(self.command_edit)
        row2.addWidget(self.send_btn)
        row2.addWidget(self.status_btn)

        self.console = QtWidgets.QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(1000)

        layout.addLayout(row0)
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addWidget(self.console)

        self.apply_algo_btn.clicked.connect(self._send_alg)
        self.set_ref_btn.clicked.connect(self._send_ref)
        self.run_btn.clicked.connect(lambda: self._send_direct("RUN 1"))
        self.stop_btn.clicked.connect(lambda: self._send_direct("RUN 0"))
        self.send_btn.clicked.connect(self._send_from_edit)
        self.status_btn.clicked.connect(lambda: self._send_direct("GET STATUS"))
        self.command_edit.returnPressed.connect(self._send_from_edit)

    def _send_alg(self):
        algo = self.algo_combo.currentText().strip()
        self.algo_selected.emit(algo)
        self._send_direct(f"ALG {algo}")

    def _send_ref(self):
        val = self.ref_spin.value()
        self.ref_changed.emit(val)
        self._send_direct(f"SET REF {val:.3f}")

    def _send_direct(self, command: str):
        self.send_command.emit(command)
        self.append_console(f"> {command}")

    def _send_from_edit(self):
        cmd = self.command_edit.text().strip()
        if not cmd:
            return
        self._history.append(cmd)
        self._history_idx = len(self._history)
        self._send_direct(cmd)
        self.command_edit.clear()

    def append_console(self, line: str):
        self.console.appendPlainText(line)

