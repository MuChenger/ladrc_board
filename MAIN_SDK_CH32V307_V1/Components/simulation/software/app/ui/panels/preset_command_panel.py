from PyQt5 import QtCore, QtWidgets


class PresetCommandPanel(QtWidgets.QGroupBox):
    send_command = QtCore.pyqtSignal(str)

    TYPE_NONE = "none"
    TYPE_INT = "int"
    TYPE_FLOAT = "float"
    TYPE_TEXT = "text"

    DEFAULT_PRESETS = [
        ("状态查询", "GET STATUS", TYPE_NONE, ""),
        ("比例参数", "SET KP", TYPE_FLOAT, 1.20),
        ("积分参数", "SET KI", TYPE_FLOAT, 0.30),
        ("微分参数", "SET KD", TYPE_FLOAT, 0.05),
        ("参考目标", "SET REF", TYPE_FLOAT, 2.00),
    ]

    def __init__(self, parent=None):
        super().__init__("默认命令框", parent)
        self._rows = []
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)

        hint = QtWidgets.QLabel("可直接修改命令名称、参数类型和参数值，再一键发送。")
        hint.setObjectName("statusHint")
        layout.addWidget(hint)

        for display_name, command_name, param_type, value in self.DEFAULT_PRESETS:
            row_frame = QtWidgets.QFrame()
            row_frame.setObjectName("presetRow")
            row_layout = QtWidgets.QGridLayout(row_frame)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setHorizontalSpacing(8)
            row_layout.setVerticalSpacing(6)

            name_label = QtWidgets.QLabel(display_name)
            name_label.setMinimumWidth(70)

            command_edit = QtWidgets.QLineEdit(command_name)

            type_combo = QtWidgets.QComboBox()
            type_combo.addItem("无参数", self.TYPE_NONE)
            type_combo.addItem("整数", self.TYPE_INT)
            type_combo.addItem("浮点", self.TYPE_FLOAT)
            type_combo.addItem("文本", self.TYPE_TEXT)

            value_stack = QtWidgets.QStackedWidget()
            none_label = QtWidgets.QLabel("无需参数")
            none_label.setAlignment(QtCore.Qt.AlignCenter)

            int_spin = QtWidgets.QSpinBox()
            int_spin.setRange(-999999, 999999)

            float_spin = QtWidgets.QDoubleSpinBox()
            float_spin.setRange(-999999.0, 999999.0)
            float_spin.setDecimals(3)
            float_spin.setSingleStep(0.1)

            text_edit = QtWidgets.QLineEdit()
            text_edit.setPlaceholderText("输入文本参数")

            value_stack.addWidget(none_label)
            value_stack.addWidget(int_spin)
            value_stack.addWidget(float_spin)
            value_stack.addWidget(text_edit)

            send_btn = QtWidgets.QPushButton("发送")
            send_btn.setMinimumWidth(self.fontMetrics().horizontalAdvance(send_btn.text()) + 28)

            row_layout.addWidget(name_label, 0, 0)
            row_layout.addWidget(command_edit, 0, 1)
            row_layout.addWidget(type_combo, 0, 2)
            row_layout.addWidget(value_stack, 0, 3)
            row_layout.addWidget(send_btn, 0, 4)
            row_layout.setColumnStretch(1, 1)
            row_layout.setColumnStretch(3, 1)

            row = {
                "command_edit": command_edit,
                "type_combo": type_combo,
                "value_stack": value_stack,
                "int_spin": int_spin,
                "float_spin": float_spin,
                "text_edit": text_edit,
            }
            self._rows.append(row)

            self._apply_row_defaults(row, param_type, value)
            type_combo.currentIndexChanged.connect(lambda _=None, item=row: self._sync_row_type(item))
            send_btn.clicked.connect(lambda _=None, item=row: self._send_row_command(item))
            layout.addWidget(row_frame)

    def _apply_row_defaults(self, row: dict, param_type: str, value):
        combo = row["type_combo"]
        index = combo.findData(param_type)
        combo.setCurrentIndex(max(index, 0))
        if param_type == self.TYPE_INT:
            row["int_spin"].setValue(int(value))
        elif param_type == self.TYPE_FLOAT:
            row["float_spin"].setValue(float(value))
        elif param_type == self.TYPE_TEXT:
            row["text_edit"].setText(str(value))
        self._sync_row_type(row)

    def _sync_row_type(self, row: dict):
        param_type = row["type_combo"].currentData()
        page_map = {
            self.TYPE_NONE: 0,
            self.TYPE_INT: 1,
            self.TYPE_FLOAT: 2,
            self.TYPE_TEXT: 3,
        }
        row["value_stack"].setCurrentIndex(page_map.get(param_type, 0))

    def _send_row_command(self, row: dict):
        command = row["command_edit"].text().strip()
        if not command:
            return

        param_type = row["type_combo"].currentData()
        if param_type == self.TYPE_NONE:
            final_command = command
        elif param_type == self.TYPE_INT:
            final_command = f"{command} {row['int_spin'].value()}"
        elif param_type == self.TYPE_FLOAT:
            final_command = f"{command} {row['float_spin'].value():.3f}"
        else:
            text = row["text_edit"].text().strip()
            final_command = command if not text else f"{command} {text}"

        self.send_command.emit(final_command)
