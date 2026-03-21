from PyQt5 import QtCore, QtWidgets


class SerialPanel(QtWidgets.QGroupBox):
    refresh_requested = QtCore.pyqtSignal()
    connect_requested = QtCore.pyqtSignal(str, int)
    disconnect_requested = QtCore.pyqtSignal()
    binary_tx_changed = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__("串口连接", parent)
        self._build()

    def _build(self):
        layout = QtWidgets.QGridLayout(self)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setMinimumWidth(140)

        self.baud_combo = QtWidgets.QComboBox()
        self.baud_combo.addItems(["115200", "230400", "460800", "921600"])
        self.baud_combo.setCurrentText("115200")

        self.refresh_btn = QtWidgets.QPushButton("刷新")
        self.connect_btn = QtWidgets.QPushButton("连接")
        self.disconnect_btn = QtWidgets.QPushButton("断开")
        self.disconnect_btn.setEnabled(False)

        self.binary_cb = QtWidgets.QCheckBox("使用二进制回传")
        self.binary_cb.setChecked(True)

        self.state_label = QtWidgets.QLabel("未连接")
        self.state_label.setObjectName("statusHint")

        layout.addWidget(QtWidgets.QLabel("端口"), 0, 0)
        layout.addWidget(self.port_combo, 0, 1, 1, 2)
        layout.addWidget(QtWidgets.QLabel("波特率"), 1, 0)
        layout.addWidget(self.baud_combo, 1, 1, 1, 2)
        layout.addWidget(self.refresh_btn, 2, 0)
        layout.addWidget(self.connect_btn, 2, 1)
        layout.addWidget(self.disconnect_btn, 2, 2)
        layout.addWidget(self.binary_cb, 3, 0, 1, 3)
        layout.addWidget(self.state_label, 4, 0, 1, 3)

        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.connect_btn.clicked.connect(self._on_connect)
        self.disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        self.binary_cb.toggled.connect(self.binary_tx_changed.emit)

        metrics = self.fontMetrics()
        for button in (self.refresh_btn, self.connect_btn, self.disconnect_btn):
            button.setMinimumWidth(metrics.horizontalAdvance(button.text()) + 28)

    def _on_connect(self):
        self.connect_requested.emit(self.port_combo.currentText(), int(self.baud_combo.currentText()))

    def set_ports(self, ports):
        current = self.port_combo.currentText()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if current in ports:
            self.port_combo.setCurrentText(current)

    def set_connected(self, connected: bool, desc: str = ""):
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self.state_label.setText(f"已连接 {desc}".strip() if connected else "未连接")

    def get_state(self) -> dict:
        return {
            "port": self.port_combo.currentText(),
            "baud": self.baud_combo.currentText(),
            "binary": self.binary_cb.isChecked(),
        }

    def apply_state(self, state: dict):
        if not isinstance(state, dict):
            return
        port = str(state.get("port", "")).strip()
        if port:
            index = self.port_combo.findText(port)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)

        baud = str(state.get("baud", "")).strip()
        if baud:
            index = self.baud_combo.findText(baud)
            if index >= 0:
                self.baud_combo.setCurrentIndex(index)

        if "binary" in state:
            self.binary_cb.setChecked(bool(state.get("binary")))

    def reset_to_defaults(self):
        if self.port_combo.count() > 0:
            self.port_combo.setCurrentIndex(0)
        baud_index = self.baud_combo.findText("115200")
        self.baud_combo.setCurrentIndex(max(baud_index, 0))
        self.binary_cb.setChecked(True)
