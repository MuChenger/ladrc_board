from PyQt5 import QtCore, QtWidgets


class NoWheelComboBox(QtWidgets.QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class PresetCommandPanel(QtWidgets.QGroupBox):
    send_command = QtCore.pyqtSignal(str)

    TYPE_NONE = "none"
    TYPE_INT = "int"
    TYPE_FLOAT = "float"
    TYPE_TEXT = "text"

    LEGACY_DEFAULT_PRESETS = [
        {"name": "状态查询", "command": "GET STATUS", "type": TYPE_NONE, "value": ""},
        {"name": "比例参数", "command": "SET KP", "type": TYPE_FLOAT, "value": 1.20},
        {"name": "积分参数", "command": "SET KI", "type": TYPE_FLOAT, "value": 0.30},
        {"name": "微分参数", "command": "SET KD", "type": TYPE_FLOAT, "value": 0.05},
        {"name": "参考目标", "command": "SET REF", "type": TYPE_FLOAT, "value": 2.00},
    ]
    PREVIOUS_PID_DEFAULT_PRESETS = [
        {"name": "状态查询", "command": "GET STATUS", "type": TYPE_NONE, "value": ""},
        {"name": "切换 PID", "command": "ALG PID", "type": TYPE_NONE, "value": ""},
        {"name": "PID 比例 KP", "command": "SET KP", "type": TYPE_FLOAT, "value": 1.20},
        {"name": "PID 积分 KI", "command": "SET KI", "type": TYPE_FLOAT, "value": 0.30},
        {"name": "PID 微分 KD", "command": "SET KD", "type": TYPE_FLOAT, "value": 0.05},
    ]
    DEFAULT_PRESETS = [
        {"name": "状态查询", "command": "GET STATUS", "type": TYPE_NONE, "value": ""},
        {"name": "预设参数", "command": "ALG PID", "type": TYPE_NONE, "value": ""},
        {"name": "预设参数", "command": "SET KP", "type": TYPE_FLOAT, "value": 1.20},
        {"name": "预设参数", "command": "SET KI", "type": TYPE_FLOAT, "value": 0.30},
        {"name": "预设参数", "command": "SET KD", "type": TYPE_FLOAT, "value": 0.05},
    ]

    def __init__(self, parent=None):
        super().__init__("命令预设", parent)
        self._loading_preset = False
        self._presets = [dict(item) for item in self.DEFAULT_PRESETS]
        self._build()
        self._load_presets()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        hint = QtWidgets.QLabel("默认提供 5 个预设命令，也可以通过下拉框选择、手动编辑并继续添加新的选项。")
        hint.setObjectName("statusHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        selector_label = QtWidgets.QLabel("预设选项")
        selector_label.setObjectName("statusHint")
        self.preset_combo = NoWheelComboBox()
        self.preset_combo.setMinimumContentsLength(10)
        self.preset_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.add_btn = QtWidgets.QPushButton("添加选项")
        self.save_btn = QtWidgets.QPushButton("保存当前")

        selector_actions = QtWidgets.QHBoxLayout()
        selector_actions.setSpacing(8)
        selector_actions.addWidget(self.add_btn)
        selector_actions.addWidget(self.save_btn)
        selector_actions.addStretch(1)

        name_label = QtWidgets.QLabel("选项名称")
        name_label.setObjectName("statusHint")
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("例如：高度查询")

        command_label = QtWidgets.QLabel("命令名称")
        command_label.setObjectName("statusHint")
        self.command_edit = QtWidgets.QLineEdit()
        self.command_edit.setPlaceholderText("例如：GET STATUS")

        type_label = QtWidgets.QLabel("参数类型")
        type_label.setObjectName("statusHint")
        self.type_combo = NoWheelComboBox()
        self.type_combo.addItem("无参数", self.TYPE_NONE)
        self.type_combo.addItem("整数", self.TYPE_INT)
        self.type_combo.addItem("浮点", self.TYPE_FLOAT)
        self.type_combo.addItem("文本", self.TYPE_TEXT)

        value_label = QtWidgets.QLabel("参数值")
        value_label.setObjectName("statusHint")
        self.value_stack = QtWidgets.QStackedWidget()
        self.value_stack.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        none_label = QtWidgets.QLabel("当前模式无需参数")
        none_label.setAlignment(QtCore.Qt.AlignCenter)

        self.int_spin = QtWidgets.QSpinBox()
        self.int_spin.setRange(-999999, 999999)

        self.float_spin = QtWidgets.QDoubleSpinBox()
        self.float_spin.setRange(-999999.0, 999999.0)
        self.float_spin.setDecimals(3)
        self.float_spin.setSingleStep(0.1)

        self.text_edit = QtWidgets.QLineEdit()
        self.text_edit.setPlaceholderText("输入文本参数")

        self.value_stack.addWidget(none_label)
        self.value_stack.addWidget(self.int_spin)
        self.value_stack.addWidget(self.float_spin)
        self.value_stack.addWidget(self.text_edit)

        action_row = QtWidgets.QHBoxLayout()
        action_row.setSpacing(8)
        self.send_btn = QtWidgets.QPushButton("发送命令")
        self.reset_btn = QtWidgets.QPushButton("恢复默认")
        action_row.addStretch(1)
        action_row.addWidget(self.reset_btn)
        action_row.addWidget(self.send_btn)

        layout.addWidget(selector_label)
        layout.addWidget(self.preset_combo)
        layout.addLayout(selector_actions)
        layout.addWidget(name_label)
        layout.addWidget(self.name_edit)
        layout.addWidget(command_label)
        layout.addWidget(self.command_edit)
        layout.addWidget(type_label)
        layout.addWidget(self.type_combo)
        layout.addWidget(value_label)
        layout.addWidget(self.value_stack)
        layout.addLayout(action_row)

        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.type_combo.currentIndexChanged.connect(self._sync_value_editor)
        self.add_btn.clicked.connect(self._add_preset)
        self.save_btn.clicked.connect(self._save_current_preset)
        self.reset_btn.clicked.connect(self._reset_to_default)
        self.send_btn.clicked.connect(self._send_current_command)

        metrics = self.fontMetrics()
        for button in (self.add_btn, self.save_btn, self.send_btn, self.reset_btn):
            button.setMinimumWidth(metrics.horizontalAdvance(button.text()) + 28)

    def _load_presets(self):
        blocker = QtCore.QSignalBlocker(self.preset_combo)
        self.preset_combo.clear()
        for preset in self._presets:
            self.preset_combo.addItem(preset["name"])
        del blocker
        self.preset_combo.setCurrentIndex(0)
        self._load_preset_to_editor(0)

    def _current_value(self):
        param_type = self.type_combo.currentData()
        if param_type == self.TYPE_NONE:
            return ""
        if param_type == self.TYPE_INT:
            return self.int_spin.value()
        if param_type == self.TYPE_FLOAT:
            return self.float_spin.value()
        return self.text_edit.text().strip()

    def _sync_value_editor(self):
        page_map = {
            self.TYPE_NONE: 0,
            self.TYPE_INT: 1,
            self.TYPE_FLOAT: 2,
            self.TYPE_TEXT: 3,
        }
        self.value_stack.setCurrentIndex(page_map.get(self.type_combo.currentData(), 0))

    def _load_preset_to_editor(self, index: int):
        if index < 0 or index >= len(self._presets):
            return
        preset = self._presets[index]
        self._loading_preset = True
        try:
            self.name_edit.setText(str(preset["name"]))
            self.command_edit.setText(str(preset["command"]))

            combo_index = self.type_combo.findData(preset["type"])
            self.type_combo.setCurrentIndex(max(combo_index, 0))

            if preset["type"] == self.TYPE_INT:
                self.int_spin.setValue(int(preset["value"]))
            elif preset["type"] == self.TYPE_FLOAT:
                self.float_spin.setValue(float(preset["value"]))
            elif preset["type"] == self.TYPE_TEXT:
                self.text_edit.setText(str(preset["value"]))
            else:
                self.text_edit.clear()
            self._sync_value_editor()
        finally:
            self._loading_preset = False

    def _collect_editor_state(self):
        name = self.name_edit.text().strip() or "未命名选项"
        command = self.command_edit.text().strip()
        param_type = self.type_combo.currentData()
        value = self._current_value()
        return {
            "name": name,
            "command": command,
            "type": param_type,
            "value": value,
        }

    def _on_preset_changed(self, index: int):
        if self._loading_preset:
            return
        self._load_preset_to_editor(index)

    def _add_preset(self):
        preset = self._collect_editor_state()
        if not preset["command"]:
            return
        self._presets.append(preset)
        self.preset_combo.addItem(preset["name"])
        self.preset_combo.setCurrentIndex(self.preset_combo.count() - 1)

    def _save_current_preset(self):
        index = self.preset_combo.currentIndex()
        if index < 0 or index >= len(self._presets):
            return
        preset = self._collect_editor_state()
        if not preset["command"]:
            return
        self._presets[index] = preset
        self.preset_combo.setItemText(index, preset["name"])

    def _reset_to_default(self):
        self._presets = [dict(item) for item in self.DEFAULT_PRESETS]
        self._load_presets()

    def _presets_match(self, left, right):
        if len(left) != len(right):
            return False
        for left_item, right_item in zip(left, right):
            if not isinstance(left_item, dict) or not isinstance(right_item, dict):
                return False
            if str(left_item.get("command", "")).strip().upper() != str(right_item.get("command", "")).strip().upper():
                return False
            if str(left_item.get("type", self.TYPE_NONE)) != str(right_item.get("type", self.TYPE_NONE)):
                return False
        return True

    def _rename_to_current_default_names(self, presets):
        renamed = []
        for index, item in enumerate(presets):
            current = dict(item)
            current["name"] = self.DEFAULT_PRESETS[index]["name"]
            renamed.append(current)
        return renamed

    def _send_current_command(self):
        preset = self._collect_editor_state()
        command = preset["command"]
        if not command:
            return

        if preset["type"] == self.TYPE_NONE:
            final_command = command
        elif preset["type"] == self.TYPE_INT:
            final_command = f"{command} {int(preset['value'])}"
        elif preset["type"] == self.TYPE_FLOAT:
            final_command = f"{command} {float(preset['value']):.3f}"
        else:
            text = str(preset["value"]).strip()
            final_command = command if not text else f"{command} {text}"

        self.send_command.emit(final_command)

    def get_state(self) -> dict:
        return {
            "presets": [dict(item) for item in self._presets],
            "current_index": int(self.preset_combo.currentIndex()),
            "editor_state": self._collect_editor_state(),
        }

    def apply_state(self, state: dict):
        if not isinstance(state, dict):
            return

        migrated_from_defaults = False
        presets = state.get("presets")
        if isinstance(presets, list) and presets:
            normalized = []
            for item in presets:
                if not isinstance(item, dict):
                    continue
                command = str(item.get("command", "")).strip()
                if not command:
                    continue
                normalized.append(
                    {
                        "name": str(item.get("name", "")).strip() or "未命名选项",
                        "command": command,
                        "type": item.get("type", self.TYPE_NONE),
                        "value": item.get("value", ""),
                    }
                )
            if normalized:
                if self._presets_match(normalized, self.LEGACY_DEFAULT_PRESETS):
                    normalized = [dict(item) for item in self.DEFAULT_PRESETS]
                    migrated_from_defaults = True
                elif self._presets_match(normalized, self.PREVIOUS_PID_DEFAULT_PRESETS) or self._presets_match(normalized, self.DEFAULT_PRESETS):
                    normalized = self._rename_to_current_default_names(normalized)
                    migrated_from_defaults = True
                self._presets = normalized
                self._load_presets()

        index = state.get("current_index")
        if isinstance(index, int) and 0 <= index < self.preset_combo.count():
            self.preset_combo.setCurrentIndex(index)

        editor_state = state.get("editor_state")
        if isinstance(editor_state, dict) and not migrated_from_defaults:
            self.name_edit.setText(str(editor_state.get("name", self.name_edit.text())))
            self.command_edit.setText(str(editor_state.get("command", self.command_edit.text())))
            combo_index = self.type_combo.findData(editor_state.get("type", self.TYPE_NONE))
            self.type_combo.setCurrentIndex(max(combo_index, 0))
            value = editor_state.get("value", "")
            if self.type_combo.currentData() == self.TYPE_INT:
                try:
                    self.int_spin.setValue(int(value))
                except (TypeError, ValueError):
                    pass
            elif self.type_combo.currentData() == self.TYPE_FLOAT:
                try:
                    self.float_spin.setValue(float(value))
                except (TypeError, ValueError):
                    pass
            elif self.type_combo.currentData() == self.TYPE_TEXT:
                self.text_edit.setText(str(value))
            self._sync_value_editor()

    def reset_to_defaults(self):
        self._reset_to_default()
