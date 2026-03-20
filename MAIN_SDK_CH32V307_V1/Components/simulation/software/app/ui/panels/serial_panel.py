from PyQt5 import QtCore, QtWidgets


class SerialPanel(QtWidgets.QGroupBox):
    refresh_requested = QtCore.pyqtSignal()
    connect_requested = QtCore.pyqtSignal(str, int)
    disconnect_requested = QtCore.pyqtSignal()
    binary_tx_changed = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__("Serial", parent)
        self.setMinimumWidth(320)
        self._build()

    def _build(self):
        layout = QtWidgets.QGridLayout(self)

        self.port_combo = QtWidgets.QComboBox()
        self.baud_combo = QtWidgets.QComboBox()
        self.baud_combo.addItems(["115200", "230400", "460800", "921600"])
        self.baud_combo.setCurrentText("115200")

        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.connect_btn = QtWidgets.QPushButton("Connect")
        self.disconnect_btn = QtWidgets.QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        self.binary_cb = QtWidgets.QCheckBox("Binary TX")
        self.binary_cb.setChecked(True)

        self.state_label = QtWidgets.QLabel("Disconnected")

        layout.addWidget(QtWidgets.QLabel("Port"), 0, 0)
        layout.addWidget(self.port_combo, 0, 1, 1, 2)
        layout.addWidget(QtWidgets.QLabel("Baud"), 1, 0)
        layout.addWidget(self.baud_combo, 1, 1, 1, 2)
        layout.addWidget(self.refresh_btn, 2, 0)
        layout.addWidget(self.connect_btn, 2, 1)
        layout.addWidget(self.disconnect_btn, 2, 2)
        layout.addWidget(self.binary_cb, 3, 0, 1, 2)
        layout.addWidget(self.state_label, 4, 0, 1, 3)

        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.connect_btn.clicked.connect(self._on_connect)
        self.disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        self.binary_cb.toggled.connect(self.binary_tx_changed.emit)

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
        self.state_label.setText(f"Connected: {desc}" if connected else "Disconnected")

