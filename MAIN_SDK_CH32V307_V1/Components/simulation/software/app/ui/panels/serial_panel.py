from PyQt5 import QtCore, QtWidgets


class SerialPanel(QtWidgets.QGroupBox):
    refresh_requested = QtCore.pyqtSignal()
    connect_requested = QtCore.pyqtSignal(str, int)
    disconnect_requested = QtCore.pyqtSignal()
    binary_tx_changed = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__("串口连接", parent)
        self.setObjectName("sidePanel")
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        header_card = QtWidgets.QFrame()
        header_card.setObjectName("panelHero")
        header_layout = QtWidgets.QHBoxLayout(header_card)
        header_layout.setContentsMargins(6, 5, 6, 5)
        header_layout.setSpacing(5)

        title_layout = QtWidgets.QVBoxLayout()
        title_layout.setSpacing(2)
        eyebrow = QtWidgets.QLabel("设备")
        eyebrow.setObjectName("panelEyebrow")
        title = QtWidgets.QLabel("串口连接")
        title.setObjectName("panelHeroTitle")
        subtitle = QtWidgets.QLabel("选择端口并连接下位机")
        subtitle.setObjectName("panelHeroSubtitle")
        subtitle.setWordWrap(True)
        title_layout.addWidget(eyebrow)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout, 1)

        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setMinimumWidth(0)
        self.port_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.baud_combo = QtWidgets.QComboBox()
        self.baud_combo.addItems(["9600", "115200", "230400", "460800", "921600"])
        self.baud_combo.setCurrentText("115200")
        self.baud_combo.setMinimumWidth(96)
        self.baud_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.refresh_btn = QtWidgets.QPushButton("刷新")
        self.connect_btn = QtWidgets.QPushButton("连接")
        self.disconnect_btn = QtWidgets.QPushButton("断开")
        self.disconnect_btn.setEnabled(False)

        self.binary_cb = QtWidgets.QCheckBox("旧链路二进制反馈")
        self.binary_cb.setToolTip("当前仓库的 LADRC 下位机主要使用 # 命令链路，此选项仅用于兼容旧版反馈回传方案。")
        self.binary_cb.setChecked(False)

        self.state_label = QtWidgets.QLabel("未连接")
        self.state_label.setObjectName("panelBadge")
        self.state_label.setAlignment(QtCore.Qt.AlignCenter)
        self.state_label.setProperty("connected", False)
        self.state_label.setMinimumWidth(64)
        header_layout.addWidget(self.state_label, 0, QtCore.Qt.AlignTop)
        layout.addWidget(header_card)

        connection_card = QtWidgets.QFrame()
        connection_card.setObjectName("panelCard")
        connection_layout = QtWidgets.QVBoxLayout(connection_card)
        connection_layout.setContentsMargins(6, 6, 6, 6)
        connection_layout.setSpacing(4)

        connection_title = QtWidgets.QLabel("连接配置")
        connection_title.setObjectName("panelCardTitle")
        connection_layout.addWidget(connection_title)
        connection_title.setToolTip("设置串口端口和波特率，然后执行连接或断开。")

        form_grid = QtWidgets.QGridLayout()
        form_grid.setHorizontalSpacing(4)
        form_grid.setVerticalSpacing(4)
        form_grid.addWidget(self._field_label("端口"), 0, 0)
        form_grid.addWidget(self.port_combo, 0, 1)
        form_grid.addWidget(self._field_label("波特率"), 1, 0)
        form_grid.addWidget(self.baud_combo, 1, 1)
        form_grid.setColumnStretch(1, 1)
        connection_layout.addLayout(form_grid)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(4)
        self.refresh_btn.setProperty("secondaryRole", True)
        self.connect_btn.setProperty("accentRole", True)
        self.disconnect_btn.setProperty("dangerRole", True)
        button_row.addWidget(self.refresh_btn)
        button_row.addWidget(self.connect_btn)
        button_row.addWidget(self.disconnect_btn)
        button_row.addStretch(1)
        connection_layout.addLayout(button_row)
        layout.addWidget(connection_card)

        option_card = QtWidgets.QFrame()
        option_card.setObjectName("panelCard")
        option_layout = QtWidgets.QVBoxLayout(option_card)
        option_layout.setContentsMargins(6, 6, 6, 6)
        option_layout.setSpacing(4)

        option_title = QtWidgets.QLabel("链路兼容")
        option_title.setObjectName("panelCardTitle")
        option_layout.addWidget(option_title)
        option_title.setToolTip("当前推荐使用文本命令链路；仅在兼容旧工程时启用二进制反馈。")
        option_layout.addWidget(self.binary_cb)
        layout.addWidget(option_card)
        layout.addStretch(1)

        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.connect_btn.clicked.connect(self._on_connect)
        self.disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        self.binary_cb.toggled.connect(self.binary_tx_changed.emit)

        metrics = self.fontMetrics()
        for button in (self.refresh_btn, self.connect_btn, self.disconnect_btn):
            button.setMinimumWidth(metrics.horizontalAdvance(button.text()) + 10)

    def _field_label(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setObjectName("panelFieldLabel")
        return label

    def _refresh_state_badge_style(self):
        style = self.state_label.style()
        if style is not None:
            style.unpolish(self.state_label)
            style.polish(self.state_label)

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
        self.state_label.setProperty("connected", bool(connected))
        self._refresh_state_badge_style()

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
        self.binary_cb.setChecked(False)
