import math
import time
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets


class _NoWheelComboBox(QtWidgets.QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class _NoWheelSpinBoxMixin:
    def wheelEvent(self, event):
        event.ignore()


class NoWheelSpinBox(_NoWheelSpinBoxMixin, QtWidgets.QSpinBox):
    pass


class NoWheelDoubleSpinBox(_NoWheelSpinBoxMixin, QtWidgets.QDoubleSpinBox):
    pass


class DecimalInput(QtWidgets.QLineEdit):
    valueChanged = QtCore.pyqtSignal(float)

    def wheelEvent(self, event):
        event.ignore()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._minimum = -1_000_000_000.0
        self._maximum = 1_000_000_000.0
        self._decimals = 3
        self._single_step = 0.1
        self._value = 0.0
        self._validator = QtGui.QDoubleValidator(self)
        self._validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        self.setValidator(self._validator)
        self.setAlignment(QtCore.Qt.AlignRight)
        self.setMinimumWidth(88)
        self.setMaximumWidth(110)
        self.textEdited.connect(self._on_text_edited)
        self._sync_validator()
        self.setValue(0.0)

    def lineEdit(self):
        return self

    def setRange(self, minimum: float, maximum: float):
        self._minimum = float(minimum)
        self._maximum = float(maximum)
        self._sync_validator()
        self.setValue(self._value)

    def setDecimals(self, decimals: int):
        self._decimals = max(0, int(decimals))
        self._sync_validator()
        self.setValue(self._value)

    def setSingleStep(self, step: float):
        self._single_step = float(step)

    def setKeyboardTracking(self, _enabled: bool):
        return

    def value(self) -> float:
        parsed = self._coerce_text(self.text())
        if parsed is not None:
            return parsed
        return float(self._value)

    def setValue(self, value: float):
        numeric = self._clamp(value)
        changed = not math.isclose(numeric, self._value, rel_tol=0.0, abs_tol=10 ** (-(self._decimals + 1)))
        self._value = numeric
        formatted = self._format_value(numeric)
        if self.text() != formatted:
            super().setText(formatted)
        if changed:
            self.valueChanged.emit(self._value)

    def interpretText(self):
        parsed = self._coerce_text(self.text())
        self.setValue(self._value if parsed is None else parsed)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QtCore.QTimer.singleShot(0, self.selectAll)

    def _sync_validator(self):
        self._validator.setBottom(self._minimum)
        self._validator.setTop(self._maximum)
        self._validator.setDecimals(self._decimals)

    def _clamp(self, value: float) -> float:
        numeric = float(value)
        if not math.isfinite(numeric):
            numeric = self._value
        return max(self._minimum, min(self._maximum, numeric))

    def _format_value(self, value: float) -> str:
        text = f"{float(value):.{self._decimals}f}".rstrip("0").rstrip(".")
        if text in {"", "-0"}:
            return "0"
        return text

    def _coerce_text(self, text: str) -> Optional[float]:
        raw = str(text).strip()
        if not raw or raw in {"-", ".", "-."}:
            return None
        try:
            return self._clamp(float(raw))
        except (TypeError, ValueError):
            return None

    def _on_text_edited(self, text: str):
        parsed = self._coerce_text(text)
        if parsed is None:
            return
        if math.isclose(parsed, self._value, rel_tol=0.0, abs_tol=10 ** (-(self._decimals + 1))):
            return
        self._value = parsed
        self.valueChanged.emit(self._value)


def _format_numeric_payload(value: float) -> str:
    numeric = float(value)
    payload = f"{numeric:.6f}".rstrip("0").rstrip(".")
    if payload in {"", "-0"}:
        return "0"
    return payload


def _normalize_numeric_payload(payload: object) -> Optional[str]:
    try:
        return _format_numeric_payload(float(payload))
    except (TypeError, ValueError):
        return None


def _split_definition_lines(text: str):
    return [line.strip() for line in str(text).splitlines() if line.strip()]


def _parse_parameter_definitions(text: str):
    lines = _split_definition_lines(text)
    if not lines:
        raise ValueError("请至少定义一个参数。")

    parameters = []
    used_commands = set()
    for line in lines:
        if "=" in line:
            label, command = line.split("=", 1)
        else:
            label, command = line, line
        label = label.strip()
        command = command.strip()
        if not label or not command:
            raise ValueError(f"参数定义无效：{line}")
        if any(ch.isspace() for ch in command):
            raise ValueError(f"参数命令名不能包含空格：{command}")
        command_upper = command.upper()
        if command_upper in {"PID", "LADRC", "OPEN_LOOP"}:
            raise ValueError(f"参数命令名不能使用保留字：{command}")
        if command_upper in used_commands:
            raise ValueError(f"参数命令名重复：{command}")
        used_commands.add(command_upper)
        parameters.append({"label": label, "command": command, "value": 0.0})
    return parameters


def _parse_quick_command_definitions(text: str, require_at_least_one: bool = False):
    lines = _split_definition_lines(text)
    if not lines:
        if require_at_least_one:
            raise ValueError("请至少定义一个命令。")
        return []

    commands = []
    used_labels = set()
    used_commands = set()
    for line in lines:
        if "=" in line:
            label, command = line.split("=", 1)
        else:
            label, command = line, line
        label = label.strip()
        command = " ".join(command.strip().split())
        if not label or not command:
            raise ValueError(f"命令定义无效：{line}")
        label_upper = label.upper()
        command_upper = command.upper()
        if label_upper in used_labels:
            raise ValueError(f"命令按钮名称重复：{label}")
        if command_upper in used_commands:
            raise ValueError(f"命令内容重复：{command}")
        used_labels.add(label_upper)
        used_commands.add(command_upper)
        commands.append({"label": label, "command": command})
    return commands


class NewAlgorithmDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建算法页")
        self.resize(480, 460)
        self._definition = None
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("例如：SMC 仿真")
        form.addRow("算法名称", self.name_edit)

        self.param_edit = QtWidgets.QPlainTextEdit()
        self.param_edit.setPlaceholderText(
            "每行一个参数，支持“显示名”或“显示名=命令名”\n"
            "例如：\n"
            "滑模增益=k\n"
            "边界层=phi\n"
            "扰动估计"
        )
        self.param_edit.setTabChangesFocus(True)
        form.addRow("参数定义", self.param_edit)
        self.command_edit = QtWidgets.QPlainTextEdit()
        self.command_edit.setPlaceholderText(
            "可选：每行一个快捷命令，支持“按钮名”或“按钮名=完整命令”\n"
            "例如：\n"
            "读取状态=#stat:1\n"
            "进入待机=#run:2\n"
            "自检=SELFTEST"
        )
        self.command_edit.setTabChangesFocus(True)
        self.command_edit.setFixedHeight(110)
        form.addRow("命令定义", self.command_edit)
        layout.addLayout(form)

        hint = QtWidgets.QLabel(
            "说明：显示名用于界面展示；命令名用于发送 SET <命令名> <值>。"
        )
        hint.setWordWrap(True)
        hint.setObjectName("statusHint")
        layout.addWidget(hint)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def definition(self) -> Optional[dict]:
        return self._definition

    def accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "名称缺失", "请先填写算法名称。")
            return

        lines = [line.strip() for line in self.param_edit.toPlainText().splitlines() if line.strip()]
        if not lines:
            QtWidgets.QMessageBox.warning(self, "参数缺失", "请至少定义一个参数。")
            return

        parameters = []
        used_commands = set()
        for line in lines:
            if "=" in line:
                label, command = line.split("=", 1)
            else:
                label, command = line, line
            label = label.strip()
            command = command.strip()
            if not label or not command:
                QtWidgets.QMessageBox.warning(self, "格式错误", f"参数定义无效：{line}")
                return
            if any(ch.isspace() for ch in command):
                QtWidgets.QMessageBox.warning(self, "命令名无效", f"命令名不能包含空格：{command}")
                return
            if command.upper() in {"PID", "LADRC", "OPEN_LOOP"}:
                QtWidgets.QMessageBox.warning(self, "命令名冲突", f"参数命令名不能使用保留字：{command}")
                return
            if command in used_commands:
                QtWidgets.QMessageBox.warning(self, "命令名重复", f"参数命令名重复：{command}")
                return
            used_commands.add(command)
            parameters.append({"label": label, "command": command, "value": 0.0})

        self._definition = {
            "name": name,
            "parameters": parameters,
        }
        super().accept()

def _new_algorithm_dialog_accept(self):
    name = self.name_edit.text().strip()
    if not name:
        QtWidgets.QMessageBox.warning(self, "名称缺失", "请先填写算法名称。")
        return

    try:
        parameters = _parse_parameter_definitions(self.param_edit.toPlainText())
        commands = _parse_quick_command_definitions(
            self.command_edit.toPlainText(),
            require_at_least_one=False,
        )
    except ValueError as exc:
        QtWidgets.QMessageBox.warning(self, "定义无效", str(exc))
        return

    self._definition = {
        "name": name,
        "parameters": parameters,
        "commands": commands,
    }
    super(NewAlgorithmDialog, self).accept()


NewAlgorithmDialog.accept = _new_algorithm_dialog_accept


class NewCommandDialog(QtWidgets.QDialog):
    def __init__(self, algorithm_name: str = "", parent=None):
        super().__init__(parent)
        self._algorithm_name = str(algorithm_name).strip()
        self._definitions = None
        self.setWindowTitle("新建命令")
        self.resize(440, 260)
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        if self._algorithm_name:
            summary = QtWidgets.QLabel(f"当前算法页：{self._algorithm_name}")
            summary.setObjectName("statusHint")
            summary.setWordWrap(True)
            layout.addWidget(summary)

        self.command_edit = QtWidgets.QPlainTextEdit()
        self.command_edit.setPlaceholderText(
            "每行一个快捷命令，支持“按钮名”或“按钮名=完整命令”\n"
            "例如：\n"
            "读取状态=#stat:1\n"
            "停止=#run:2\n"
            "自检=SELFTEST"
        )
        self.command_edit.setTabChangesFocus(True)
        layout.addWidget(self.command_edit)

        hint = QtWidgets.QLabel("说明：新建后会在当前自定义算法页生成快捷命令按钮。")
        hint.setWordWrap(True)
        hint.setObjectName("statusHint")
        layout.addWidget(hint)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def definitions(self):
        return self._definitions

    def accept(self):
        try:
            self._definitions = _parse_quick_command_definitions(
                self.command_edit.toPlainText(),
                require_at_least_one=True,
            )
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "命令无效", str(exc))
            return
        super().accept()


class DeleteCommandDialog(QtWidgets.QDialog):
    def __init__(self, algorithm_name: str, commands, parent=None):
        super().__init__(parent)
        self._algorithm_name = str(algorithm_name).strip()
        self._commands = list(commands or [])
        self._selected_labels = []
        self.setWindowTitle("删除命令")
        self.resize(420, 320)
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        summary = QtWidgets.QLabel(f"当前算法页：{self._algorithm_name}")
        summary.setObjectName("statusHint")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        hint = QtWidgets.QLabel("请选择要删除的快捷命令，可多选。")
        hint.setObjectName("statusHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.command_list = QtWidgets.QListWidget()
        self.command_list.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        for item in self._commands:
            label = str(item.get("label", "")).strip()
            command_text = " ".join(str(item.get("command", "")).strip().split())
            text = f"{label} -> {command_text}" if command_text else label
            list_item = QtWidgets.QListWidgetItem(text)
            list_item.setData(QtCore.Qt.UserRole, label)
            self.command_list.addItem(list_item)
        layout.addWidget(self.command_list)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_labels(self):
        return list(self._selected_labels)

    def accept(self):
        labels = []
        for item in self.command_list.selectedItems():
            label = str(item.data(QtCore.Qt.UserRole) or "").strip()
            if label:
                labels.append(label)
        if not labels:
            QtWidgets.QMessageBox.information(self, "未选择命令", "请先选择至少一个命令。")
            return
        self._selected_labels = labels
        super().accept()


class CustomAlgorithmPage(QtWidgets.QWidget):
    send_command = QtCore.pyqtSignal(str)

    def __init__(self, definition: dict, parent=None):
        super().__init__(parent)
        self._algorithm_name = ""
        self._set_command_template = "SET {command} {value}"
        self._status_command = "GET STATUS"
        self._flash_command = "SAVE FLASH"
        self._start_command = "RUN 1"
        self._stop_command = "RUN 0"
        self._parameter_widgets = []
        self._command_buttons = []
        self._command_definitions = []
        self._last_sent_payload = {}
        self._applied_signature = None
        self._advanced_panel = None
        self._advanced_btn = None
        self._command_group = None
        self._command_grid = None
        self._dirty_label = None
        self._build()
        self.apply_definition(definition)
        self.mark_applied()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.hint_label = QtWidgets.QLabel("参数名称由“文件 -> 新建算法页”定义，目标值仍使用上方“目标值设置”。")
        self.hint_label.setWordWrap(True)
        self.hint_label.setObjectName("statusHint")
        self.hint_label.hide()

        self.param_grid = QtWidgets.QGridLayout()
        self.param_grid.setHorizontalSpacing(6)
        self.param_grid.setVerticalSpacing(6)
        layout.addLayout(self.param_grid)

        self._dirty_label = QtWidgets.QLabel("参数已修改，可点击“应用配置”或“启动”生效。")
        self._dirty_label.setObjectName("statusHint")
        self._dirty_label.setWordWrap(True)
        self._dirty_label.hide()
        layout.addWidget(self._dirty_label)

        self._advanced_panel = QtWidgets.QWidget()
        advanced_layout = QtWidgets.QHBoxLayout(self._advanced_panel)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(6)
        self.apply_btn = QtWidgets.QPushButton("应用配置")
        self.status_btn = QtWidgets.QPushButton("读取状态")
        self.flash_btn = QtWidgets.QPushButton("写入FLASH")
        self.apply_btn.clicked.connect(self._apply_now)
        self.status_btn.clicked.connect(self._send_status)
        self.flash_btn.clicked.connect(self._write_flash)
        advanced_layout.addWidget(self.apply_btn)
        advanced_layout.addWidget(self.status_btn)
        advanced_layout.addWidget(self.flash_btn)
        advanced_layout.addStretch(1)
        layout.addWidget(self._advanced_panel)

        action_row = QtWidgets.QHBoxLayout()
        action_row.setSpacing(6)
        self.start_btn = QtWidgets.QPushButton("启动")
        self.stop_btn = QtWidgets.QPushButton("停止")
        self.reset_btn = QtWidgets.QPushButton("恢复默认")
        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._send_stop)
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        action_row.addWidget(self.start_btn)
        action_row.addWidget(self.stop_btn)
        action_row.addWidget(self.reset_btn)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self._command_group = QtWidgets.QGroupBox("快捷命令")
        self._command_grid = QtWidgets.QGridLayout(self._command_group)
        self._command_grid.setHorizontalSpacing(6)
        self._command_grid.setVerticalSpacing(6)
        self._command_group.hide()
        layout.addWidget(self._command_group)

    def _toggle_advanced_panel(self, expanded: bool):
        if self._advanced_panel is not None:
            self._advanced_panel.setVisible(bool(expanded))
        if self._advanced_btn is not None:
            self._advanced_btn.setArrowType(QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow)

    def _clear_param_grid(self):
        while self.param_grid.count():
            item = self.param_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._parameter_widgets = []

    def _clear_command_grid(self):
        while self._command_grid.count():
            item = self._command_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._command_buttons = []
        self._command_definitions = []

    def apply_definition(self, definition: dict):
        self._algorithm_name = str(definition.get("name", "")).strip()
        hint_text = str(
            definition.get(
                "hint",
                "参数名称由“文件 -> 新建算法页”定义，目标值仍使用上方“目标值设置”。",
            )
        ).strip()
        self._set_command_template = str(definition.get("set_command_template", "SET {command} {value}")).strip() or "SET {command} {value}"
        self._status_command = str(definition.get("status_command", "GET STATUS")).strip() or "GET STATUS"
        self._flash_command = str(definition.get("flash_command", "SAVE FLASH")).strip() or "SAVE FLASH"
        self._start_command = str(definition.get("start_command", "RUN 1")).strip() or "RUN 1"
        self._stop_command = str(definition.get("stop_command", "RUN 0")).strip() or "RUN 0"
        self.hint_label.setText(hint_text)
        self._clear_param_grid()
        self._clear_command_grid()
        parameters = definition.get("parameters", [])
        param_columns = 1
        if parameters:
            max_label_length = max(len(str(item.get("label", ""))) for item in parameters)
            if len(parameters) >= 3 and max_label_length <= 8:
                param_columns = 2
        for index, parameter in enumerate(parameters):
            label = str(parameter.get("label", f"param_{index + 1}")).strip() or f"param_{index + 1}"
            command = str(parameter.get("command", label)).strip() or label
            value = float(parameter.get("value", 0.0))
            widget = DecimalInput()
            widget.setRange(-1000.0, 1000.0)
            widget.setDecimals(3)
            widget.setSingleStep(0.1)
            widget.setKeyboardTracking(False)
            widget.setValue(value)
            widget.valueChanged.connect(self._refresh_dirty_state)
            line_edit = widget.lineEdit()
            if line_edit is not None:
                line_edit.returnPressed.connect(lambda command_name=command, editor=widget: self._commit_single_param(command_name, editor))
            row = index // param_columns
            column = (index % param_columns) * 2
            self.param_grid.addWidget(QtWidgets.QLabel(label), row, column)
            self.param_grid.addWidget(widget, row, column + 1)
            self._parameter_widgets.append(
                {
                    "label": label,
                    "command": command,
                    "default": value,
                    "widget": widget,
                }
            )
        commands = definition.get("commands", [])
        for index, command_def in enumerate(commands):
            label = str(command_def.get("label", f"命令{index + 1}")).strip() or f"命令{index + 1}"
            command_text = " ".join(str(command_def.get("command", label)).strip().split()) or label
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda _checked=False, payload=command_text: self.send_command.emit(payload))
            row = index // 2
            column = index % 2
            self._command_grid.addWidget(button, row, column)
            self._command_buttons.append(button)
            self._command_definitions.append({"label": label, "command": command_text})
        self._command_group.setVisible(bool(self._command_buttons))
        self._last_sent_payload.clear()
        self.mark_applied()

    def algorithm_name(self) -> str:
        return self._algorithm_name

    def _current_signature(self):
        return tuple(_normalize_numeric_payload(item["widget"].value()) for item in self._parameter_widgets)

    def _find_parameter_item(self, command_name: str):
        target = str(command_name).strip().upper()
        for item in self._parameter_widgets:
            if str(item["command"]).strip().upper() == target:
                return item
        return None

    @staticmethod
    def _parse_hash_command(command: str):
        raw = str(command).strip()
        if not raw.startswith("#") or ":" not in raw:
            return None, None
        command_name, payload = raw[1:].split(":", 1)
        command_name = command_name.strip()
        payload = payload.strip()
        if not command_name or not payload:
            return None, None
        return command_name, payload

    def _format_set_command(self, command_name: str, payload: str) -> str:
        return self._set_command_template.format(
            command=str(command_name),
            command_lower=str(command_name).strip().lower(),
            command_upper=str(command_name).strip().upper(),
            value=str(payload),
        )

    def mark_applied(self):
        self._applied_signature = self._current_signature()
        self._refresh_dirty_state()

    def _refresh_dirty_state(self, *_args):
        dirty = self._applied_signature is not None and self._current_signature() != self._applied_signature
        self._dirty_label.setVisible(bool(dirty))

    def definition_state(self) -> dict:
        return {
            "name": self._algorithm_name,
            "hint": self.hint_label.text(),
            "set_command_template": self._set_command_template,
            "status_command": self._status_command,
            "flash_command": self._flash_command,
            "start_command": self._start_command,
            "stop_command": self._stop_command,
            "parameters": [
                {
                    "label": item["label"],
                    "command": item["command"],
                    "value": float(item["widget"].value()),
                }
                for item in self._parameter_widgets
            ],
            "commands": [dict(item) for item in self._command_definitions],
        }

    def append_command_definitions(self, commands) -> None:
        additions = list(commands or [])
        if not additions:
            return

        merged = self.definition_state()
        existing_labels = {str(item.get("label", "")).strip().upper() for item in merged.get("commands", [])}
        existing_commands = {
            " ".join(str(item.get("command", "")).strip().split()).upper()
            for item in merged.get("commands", [])
        }
        for item in additions:
            label = str(item.get("label", "")).strip()
            command_text = " ".join(str(item.get("command", "")).strip().split())
            if not label or not command_text:
                raise ValueError("命令定义不能为空。")
            label_upper = label.upper()
            command_upper = command_text.upper()
            if label_upper in existing_labels:
                raise ValueError(f"命令按钮名称已存在：{label}")
            if command_upper in existing_commands:
                raise ValueError(f"命令内容已存在：{command_text}")
            merged.setdefault("commands", []).append({"label": label, "command": command_text})
            existing_labels.add(label_upper)
            existing_commands.add(command_upper)

        previous_signature = self._applied_signature
        self.apply_definition(merged)
        self._applied_signature = previous_signature
        self._refresh_dirty_state()

    def command_definitions(self):
        return [dict(item) for item in self._command_definitions]

    def has_commands(self) -> bool:
        return bool(self._command_definitions)

    def remove_command_labels(self, labels) -> None:
        targets = {str(label).strip().upper() for label in (labels or []) if str(label).strip()}
        if not targets:
            return

        merged = self.definition_state()
        current_commands = list(merged.get("commands", []))
        remaining = [
            dict(item)
            for item in current_commands
            if str(item.get("label", "")).strip().upper() not in targets
        ]
        if len(remaining) == len(current_commands):
            raise ValueError("未找到要删除的命令。")

        merged["commands"] = remaining
        previous_signature = self._applied_signature
        self.apply_definition(merged)
        self._applied_signature = previous_signature
        self._refresh_dirty_state()

    def build_apply_commands(self, force: bool = False):
        commands = []
        for item in self._parameter_widgets:
            payload = _format_numeric_payload(item["widget"].value())
            if not force and self._last_sent_payload.get(item["command"]) == payload:
                continue
            commands.append(self._format_set_command(item["command"], payload))
        return commands

    def _apply_now(self):
        for command in self.build_apply_commands(force=True):
            self.send_command.emit(command)
        self.mark_applied()

    def _send_status(self):
        self.send_command.emit(self._status_command)

    def _write_flash(self):
        for command in self.build_apply_commands(force=True):
            self.send_command.emit(command)
        self.send_command.emit(self._flash_command)
        self.mark_applied()

    def _start(self):
        commands = self.build_apply_commands(force=True)
        commands.append(self._start_command)
        for command in commands:
            self.send_command.emit(command)
        self.mark_applied()

    def _send_stop(self):
        self.send_command.emit(self._stop_command)

    def reset_to_defaults(self):
        for item in self._parameter_widgets:
            blocker = QtCore.QSignalBlocker(item["widget"])
            item["widget"].setValue(float(item["default"]))
            del blocker
        self._last_sent_payload.clear()
        self.mark_applied()

    def _commit_single_param(self, command_name: str, widget):
        try:
            widget.interpretText()
        except AttributeError:
            pass
        payload = _format_numeric_payload(widget.value())
        if self._last_sent_payload.get(command_name) == payload:
            return
        self.send_command.emit(self._format_set_command(command_name, payload))

    def note_command_sent(self, command: str):
        raw = " ".join(str(command).strip().split())
        if not raw:
            return
        command_name = ""
        payload = None
        parts = raw.split(" ", 2)
        if len(parts) == 3 and parts[0].upper() == "SET":
            command_name = parts[1]
            payload = _normalize_numeric_payload(parts[2])
        else:
            command_name, raw_payload = self._parse_hash_command(raw)
            if command_name:
                payload = _normalize_numeric_payload(raw_payload)
        if payload is None:
            return
        item = self._find_parameter_item(command_name)
        if item is None:
            return
        self._last_sent_payload[item["command"]] = payload

    def apply_set_command(self, command: str) -> bool:
        raw = " ".join(str(command).strip().split())
        if not raw:
            return False
        command_name = ""
        payload = None
        parts = raw.split(" ", 2)
        if len(parts) == 3 and parts[0].upper() == "SET":
            command_name = parts[1]
            payload = _normalize_numeric_payload(parts[2])
        else:
            command_name, raw_payload = self._parse_hash_command(raw)
            if command_name:
                payload = _normalize_numeric_payload(raw_payload)
        item = self._find_parameter_item(command_name)
        if item is None or payload is None:
            return False
        blocker = QtCore.QSignalBlocker(item["widget"])
        item["widget"].setValue(float(payload))
        del blocker
        self._last_sent_payload[item["command"]] = payload
        self._refresh_dirty_state()
        return True


class CommandPanel(QtWidgets.QGroupBox):
    ALGORITHM_OPTIONS = [
        ("LADRC", "LADRC"),
        ("PID", "PID"),
        ("开环", "OPEN_LOOP"),
    ]
    DISTURBANCE_LEVELS = [
        ("关闭", "off", 0.0),
        ("低", "low", 0.5),
        ("中", "medium", 1.0),
        ("高", "high", 1.6),
        ("极高", "extreme", 2.4),
    ]
    DISTURBANCE_MODES = [
        ("正弦扰动", "sine"),
        ("阶跃扰动", "step"),
        ("慢变偏置", "drift"),
    ]
    DISTURBANCE_DEFAULTS = {
        "mode": "sine",
        "amplitude_gain": 1.0,
        "frequency_gain": 1.0,
        "bias": 0.0,
    }
    LADRC_DEFAULTS = {
        "r": 20.0,
        "h": 0.02,
        "w0": 40.0,
        "wc": 2.0,
        "b0": 0.5,
        "init": 0.0,
        "expect": 0.0,
        "mode": 1,
    }
    LADRC_MODE_OPTIONS = (
        ("TD 跟踪", 0),
        ("闭环控制", 1),
    )
    LADRC_PARAM_COMMANDS = (
        ("r", "r"),
        ("h", "h"),
        ("w0", "wo"),
        ("wc", "wc"),
        ("b0", "bo"),
    )
    LADRC_TARGET_COMMANDS = (
        ("init", "init"),
        ("expect", "expe"),
    )
    LADRC_UNSAFE_RUNTIME_LIMITS = {
        "h": 0.045,
        "w0": 80.0,
        "wc": 20.0,
        "b0": 4.0,
    }
    PID_DEFAULTS = {
        "name": "PID",
        "hint": "PID 需要的参数为 KP / KI / KD，默认使用 #kp / #ki / #kd 格式，目标值仍使用上方“目标值设置”。",
        "set_command_template": "#{command_lower}:{value}",
        "status_command": "#stat:1",
        "flash_command": "#save:1",
        "start_command": "#run:1",
        "stop_command": "#run:2",
        "parameters": [
            {"label": "KP", "command": "KP", "value": 1.2},
            {"label": "KI", "command": "KI", "value": 0.3},
            {"label": "KD", "command": "KD", "value": 0.05},
        ],
    }

    send_command = QtCore.pyqtSignal(str)
    algo_selected = QtCore.pyqtSignal(str)
    ref_changed = QtCore.pyqtSignal(float)
    disturbance_level_changed = QtCore.pyqtSignal(str, float)
    disturbance_mode_changed = QtCore.pyqtSignal(str)
    disturbance_params_changed = QtCore.pyqtSignal(float, float, float)
    sim_period_changed = QtCore.pyqtSignal(int)
    simulated_upload_changed = QtCore.pyqtSignal(bool)
    console_message = QtCore.pyqtSignal(str)
    algorithm_profiles_changed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("基础控制", parent)
        self.setObjectName("sidePanel")
        self._history = []
        self._history_idx = -1
        self._ladrc_last_sent_payload = {}
        self._ladrc_applied_signature = None
        self._last_reference_edit_ms = 0
        self._reference_dirty = False
        self._built_in_algorithm_pages = {}
        self._custom_algorithm_pages = {}
        self._custom_algorithm_order = []
        self._algorithm_page_indexes = {}
        self._build()
        self._apply_size_hints()
        self._mark_ladrc_config_applied()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        header_card = QtWidgets.QFrame()
        header_card.setObjectName("panelHero")
        header_layout = QtWidgets.QHBoxLayout(header_card)
        header_layout.setContentsMargins(6, 5, 6, 5)
        header_layout.setSpacing(5)

        header_text_layout = QtWidgets.QVBoxLayout()
        header_text_layout.setSpacing(2)
        header_eyebrow = QtWidgets.QLabel("控制")
        header_eyebrow.setObjectName("panelEyebrow")
        header_title = QtWidgets.QLabel("控制工作台")
        header_title.setObjectName("panelHeroTitle")
        header_subtitle = QtWidgets.QLabel("算法切换、目标设定与运行控制")
        header_subtitle.setObjectName("panelHeroSubtitle")
        header_subtitle.setWordWrap(True)
        header_text_layout.addWidget(header_eyebrow)
        header_text_layout.addWidget(header_title)
        header_text_layout.addWidget(header_subtitle)
        header_layout.addLayout(header_text_layout, 1)

        self.algorithm_badge_label = QtWidgets.QLabel("LADRC")
        self.algorithm_badge_label.setObjectName("panelBadge")
        self.algorithm_badge_label.setAlignment(QtCore.Qt.AlignCenter)
        self.algorithm_badge_label.setMinimumWidth(64)
        header_layout.addWidget(self.algorithm_badge_label, 0, QtCore.Qt.AlignTop)
        layout.addWidget(header_card)

        def create_card(title: str, hint: str | None = None):
            card = QtWidgets.QFrame()
            card.setObjectName("panelCard")
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(6, 6, 6, 6)
            card_layout.setSpacing(3)
            title_label = QtWidgets.QLabel(title)
            title_label.setObjectName("panelCardTitle")
            card_layout.addWidget(title_label)
            if hint:
                title_label.setToolTip(hint)
                card.setToolTip(hint)
            return card, card_layout

        basic_grid = QtWidgets.QGridLayout()
        basic_grid.setHorizontalSpacing(4)
        basic_grid.setVerticalSpacing(4)
        self.algo_combo = _NoWheelComboBox()
        self.algo_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        for label, value in self.ALGORITHM_OPTIONS:
            self.algo_combo.addItem(label, value)
        self.apply_algo_btn = QtWidgets.QPushButton("应用算法")
        self.apply_algo_btn.setProperty("accentRole", True)
        self.ref_spin = DecimalInput()
        self.ref_spin.setRange(-1000.0, 1000.0)
        self.ref_spin.setDecimals(3)
        self.ref_spin.setSingleStep(0.1)
        self.ref_spin.setKeyboardTracking(False)
        self.set_ref_btn = QtWidgets.QPushButton("设置目标值")
        self.set_ref_btn.setProperty("accentRole", True)
        basic_grid.addWidget(QtWidgets.QLabel("算法"), 0, 0)
        basic_grid.addWidget(self.algo_combo, 0, 1)
        basic_grid.addWidget(self.apply_algo_btn, 0, 2)
        basic_grid.addWidget(QtWidgets.QLabel("目标值"), 1, 0)
        basic_grid.addWidget(self.ref_spin, 1, 1)
        basic_grid.addWidget(self.set_ref_btn, 1, 2)
        basic_grid.setColumnStretch(1, 1)

        disturbance_grid = QtWidgets.QGridLayout()
        disturbance_grid.setHorizontalSpacing(4)
        disturbance_grid.setVerticalSpacing(4)
        self.disturbance_combo = _NoWheelComboBox()
        self.disturbance_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        for label, key, scale in self.DISTURBANCE_LEVELS:
            self.disturbance_combo.addItem(label, (key, scale))
        self.set_disturbance_level("medium")
        self.disturbance_mode_combo = _NoWheelComboBox()
        self.disturbance_mode_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        for label, key in self.DISTURBANCE_MODES:
            self.disturbance_mode_combo.addItem(label, key)
        self.disturbance_mode_combo.setToolTip(
            "选择环境扰动形态。默认“正弦扰动”保持当前行为；"
            "“阶跃扰动”和“慢变偏置”更适合观察系统稳定后的抗扰表现。"
        )
        disturbance_grid.addWidget(QtWidgets.QLabel("扰动等级"), 0, 0)
        disturbance_grid.addWidget(self.disturbance_combo, 0, 1)
        disturbance_grid.addWidget(QtWidgets.QLabel("扰动模式"), 0, 2)
        disturbance_grid.addWidget(self.disturbance_mode_combo, 0, 3)
        self.set_disturbance_mode(self.DISTURBANCE_DEFAULTS["mode"])

        disturbance_param_grid = QtWidgets.QGridLayout()
        disturbance_param_grid.setHorizontalSpacing(4)
        disturbance_param_grid.setVerticalSpacing(4)
        self.disturbance_amp_spin = self._create_ladrc_spin(0.0, 20.0, 2, 0.1)
        self.disturbance_freq_spin = self._create_ladrc_spin(0.0, 10.0, 2, 0.1)
        self.disturbance_bias_spin = self._create_ladrc_spin(-5.0, 5.0, 3, 0.05)
        self.disturbance_amp_spin.setToolTip("环境扰动幅值倍率。默认 1.0，增大后系统稳定后也更容易观察到扰动影响。")
        self.disturbance_freq_spin.setToolTip("环境扰动频率倍率。默认 1.0，可调整扰动变化快慢。")
        self.disturbance_bias_spin.setToolTip("环境扰动偏置。默认 0.0，可模拟持续外界载荷或稳态偏差。")
        disturbance_param_grid.addWidget(QtWidgets.QLabel("幅值倍率"), 0, 0)
        disturbance_param_grid.addWidget(self.disturbance_amp_spin, 0, 1)
        disturbance_param_grid.addWidget(QtWidgets.QLabel("频率倍率"), 0, 2)
        disturbance_param_grid.addWidget(self.disturbance_freq_spin, 0, 3)
        disturbance_param_grid.addWidget(QtWidgets.QLabel("偏置"), 1, 0)
        disturbance_param_grid.addWidget(self.disturbance_bias_spin, 1, 1)
        self.set_disturbance_params(self.DISTURBANCE_DEFAULTS, emit_signal=False)

        runtime_grid = QtWidgets.QGridLayout()
        runtime_grid.setHorizontalSpacing(4)
        runtime_grid.setVerticalSpacing(4)
        runtime_grid.addWidget(QtWidgets.QLabel("运行周期"), 0, 0)
        self.sim_period_spin = NoWheelSpinBox()
        self.sim_period_spin.setRange(5, 1000)
        self.sim_period_spin.setSingleStep(5)
        self.sim_period_spin.setSuffix(" ms")
        self.sim_period_spin.setKeyboardTracking(False)
        self.sim_period_spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.sim_period_spin.setToolTip("设置上位机本地仿真的运行周期，数值越小更新越快。")
        self.sim_rate_label = QtWidgets.QLabel()
        self.sim_rate_label.setObjectName("statusHint")
        self.sim_rate_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.sim_rate_label.setFixedWidth(58)
        runtime_grid.addWidget(self.sim_period_spin, 0, 1)
        runtime_grid.addWidget(self.sim_rate_label, 0, 2)
        self.set_sim_period_ms(10, emit_signal=False)

        self.simulated_upload_cb = QtWidgets.QCheckBox("模拟下位机上传")
        self.simulated_upload_cb.setToolTip("启用后，在未连接串口时由上位机本地生成下位机遥测，便于直接体验波形、状态与 3D 联动。")
        runtime_grid.addWidget(self.simulated_upload_cb, 1, 0, 1, 3)

        action_row = QtWidgets.QHBoxLayout()
        action_row.setSpacing(4)
        self.run_btn = QtWidgets.QPushButton("启动")
        self.run_btn.setProperty("accentRole", True)
        self.stop_btn = QtWidgets.QPushButton("停止")
        self.stop_btn.setProperty("dangerRole", True)
        self.status_btn = QtWidgets.QPushButton("读取状态")
        self.status_btn.setProperty("secondaryRole", True)
        action_row.addWidget(self.run_btn)
        action_row.addWidget(self.stop_btn)
        action_row.addWidget(self.status_btn)
        action_row.addStretch(1)

        self.ladrc_group = QtWidgets.QGroupBox("LADRC 仿真")
        self.ladrc_group.setObjectName("panelSubGroup")
        algorithm_group_layout = QtWidgets.QVBoxLayout(self.ladrc_group)
        algorithm_group_layout.setContentsMargins(6, 6, 6, 6)
        algorithm_group_layout.setSpacing(6)
        self.algorithm_page_stack = QtWidgets.QStackedWidget()
        algorithm_group_layout.addWidget(self.algorithm_page_stack)

        self.ladrc_page = QtWidgets.QWidget()
        ladrc_layout = QtWidgets.QVBoxLayout(self.ladrc_page)
        ladrc_layout.setContentsMargins(0, 0, 0, 0)
        ladrc_layout.setSpacing(6)

        ladrc_param_grid = QtWidgets.QGridLayout()
        ladrc_param_grid.setHorizontalSpacing(4)
        ladrc_param_grid.setVerticalSpacing(4)
        self.ladrc_r_spin = self._create_ladrc_spin(0.0, 1000.0, 1, 1.0)
        self.ladrc_h_spin = self._create_ladrc_spin(0.001, 1.000, 3, 0.001)
        self.ladrc_w0_spin = self._create_ladrc_spin(0.0, 1000.0, 1, 1.0)
        self.ladrc_wc_spin = self._create_ladrc_spin(0.0, 1000.0, 1, 1.0)
        self.ladrc_b0_spin = self._create_ladrc_spin(0.1, 100.0, 2, 0.1)
        self.ladrc_init_spin = self._create_ladrc_spin(-1000.0, 1000.0, 3, 0.1)
        self.ladrc_expect_spin = DecimalInput()
        self.ladrc_expect_spin.setRange(-1000.0, 1000.0)
        self.ladrc_expect_spin.setDecimals(3)
        self.ladrc_expect_spin.setSingleStep(0.1)
        self.ladrc_expect_spin.setKeyboardTracking(False)
        self.ladrc_expect_spin.setToolTip("LADRC 目标值，可直接手动输入；会与上方目标值保持同步。")
        ladrc_param_grid.addWidget(QtWidgets.QLabel("r"), 0, 0)
        ladrc_param_grid.addWidget(self.ladrc_r_spin, 0, 1)
        ladrc_param_grid.addWidget(QtWidgets.QLabel("h"), 0, 2)
        ladrc_param_grid.addWidget(self.ladrc_h_spin, 0, 3)
        ladrc_param_grid.addWidget(QtWidgets.QLabel("w0"), 1, 0)
        ladrc_param_grid.addWidget(self.ladrc_w0_spin, 1, 1)
        ladrc_param_grid.addWidget(QtWidgets.QLabel("wc"), 1, 2)
        ladrc_param_grid.addWidget(self.ladrc_wc_spin, 1, 3)
        ladrc_param_grid.addWidget(QtWidgets.QLabel("b0"), 2, 0)
        ladrc_param_grid.addWidget(self.ladrc_b0_spin, 2, 1)
        ladrc_param_grid.addWidget(QtWidgets.QLabel("初值"), 2, 2)
        ladrc_param_grid.addWidget(self.ladrc_init_spin, 2, 3)
        ladrc_layout.addLayout(ladrc_param_grid)

        self.ladrc_dirty_label = QtWidgets.QLabel("参数或初值已修改，可点击“应用配置”或“启动”生效。")
        self.ladrc_dirty_label.setObjectName("statusHint")
        self.ladrc_dirty_label.setWordWrap(True)
        self.ladrc_dirty_label.hide()
        ladrc_layout.addWidget(self.ladrc_dirty_label)

        self.ladrc_advanced_panel = QtWidgets.QWidget()
        ladrc_advanced_layout = QtWidgets.QHBoxLayout(self.ladrc_advanced_panel)
        ladrc_advanced_layout.setContentsMargins(0, 0, 0, 0)
        ladrc_advanced_layout.setSpacing(6)
        self.ladrc_apply_config_btn = QtWidgets.QPushButton("应用配置")
        self.ladrc_status_btn = QtWidgets.QPushButton("读取状态")
        self.ladrc_flash_btn = QtWidgets.QPushButton("写入FLASH")
        self.ladrc_apply_config_btn.setProperty("accentRole", True)
        self.ladrc_status_btn.setProperty("secondaryRole", True)
        ladrc_advanced_layout.addWidget(self.ladrc_apply_config_btn)
        ladrc_advanced_layout.addWidget(self.ladrc_status_btn)
        ladrc_advanced_layout.addWidget(self.ladrc_flash_btn)
        ladrc_advanced_layout.addStretch(1)
        ladrc_layout.addWidget(self.ladrc_advanced_panel)

        self.ladrc_mode_combo = _NoWheelComboBox()
        self.ladrc_mode_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        for label, value in self.LADRC_MODE_OPTIONS:
            self.ladrc_mode_combo.addItem(label, value)
        self.ladrc_start_btn = QtWidgets.QPushButton("启动")
        self.ladrc_idle_btn = QtWidgets.QPushButton("停止")
        self.ladrc_reset_btn = QtWidgets.QPushButton("复位")
        self.ladrc_start_btn.setProperty("accentRole", True)
        self.ladrc_idle_btn.setProperty("dangerRole", True)
        ladrc_param_grid.addWidget(QtWidgets.QLabel("目标值"), 3, 0)
        ladrc_param_grid.addWidget(self.ladrc_expect_spin, 3, 1)
        ladrc_param_grid.addWidget(QtWidgets.QLabel("启动模式"), 3, 2)
        ladrc_param_grid.addWidget(self.ladrc_mode_combo, 3, 3)

        ladrc_button_row = QtWidgets.QHBoxLayout()
        ladrc_button_row.setSpacing(6)
        ladrc_button_row.addWidget(self.ladrc_start_btn)
        ladrc_button_row.addWidget(self.ladrc_idle_btn)
        ladrc_button_row.addWidget(self.ladrc_reset_btn)
        ladrc_button_row.addStretch(1)
        ladrc_layout.addLayout(ladrc_button_row)
        self.algorithm_page_stack.addWidget(self.ladrc_page)
        self._algorithm_page_indexes["LADRC"] = 0

        self.pid_page = CustomAlgorithmPage(self.PID_DEFAULTS, self.algorithm_page_stack)
        self.pid_page.send_command.connect(self._send_direct)
        self._built_in_algorithm_pages["PID"] = self.pid_page
        self.algorithm_page_stack.addWidget(self.pid_page)
        self._rebuild_algorithm_page_indexes()

        self._reset_ladrc_widgets()

        self.command_edit = QtWidgets.QLineEdit()
        self._refresh_command_edit_placeholder()

        send_row = QtWidgets.QHBoxLayout()
        send_row.setContentsMargins(0, 0, 0, 0)
        send_row.setSpacing(4)
        self.send_btn = QtWidgets.QPushButton("发送")
        self.send_btn.setProperty("accentRole", True)
        send_row.addWidget(self.command_edit, 1)
        send_row.addWidget(self.send_btn)

        quick_card, quick_card_layout = create_card("快速设置", "切换当前控制算法，并快速设定目标值。")
        quick_card_layout.addLayout(basic_grid)
        layout.addWidget(quick_card)

        disturbance_card, disturbance_card_layout = create_card("环境扰动", "配置上位机本地环境扰动，用于更贴近实际的联调和仿真观察。")
        disturbance_card_layout.addLayout(disturbance_grid)
        disturbance_card_layout.addLayout(disturbance_param_grid)
        layout.addWidget(disturbance_card)

        runtime_card, runtime_card_layout = create_card("仿真运行", "设置本地运行周期、模拟上传方式，并执行启动、停止或状态读取。")
        runtime_card_layout.addLayout(runtime_grid)
        runtime_card_layout.addLayout(action_row)
        layout.addWidget(runtime_card)

        algorithm_card, algorithm_card_layout = create_card("算法参数", "按当前算法显示对应配置页，LADRC 与 PID/自定义算法共用这一区域。")
        algorithm_card_layout.addWidget(self.ladrc_group)
        layout.addWidget(algorithm_card)

        command_card, command_card_layout = create_card("自定义命令", "适合临时发送调试命令，不影响当前已有的快捷配置。")
        command_card_layout.addLayout(send_row)
        layout.addWidget(command_card)
        layout.addStretch(1)

        self.apply_algo_btn.clicked.connect(self._send_alg)
        self.algo_combo.currentIndexChanged.connect(self._refresh_runtime_entry_visibility)
        self.set_ref_btn.clicked.connect(self._send_ref)
        self.run_btn.clicked.connect(self._send_runtime_start)
        self.stop_btn.clicked.connect(self._send_runtime_stop)
        self.send_btn.clicked.connect(self._send_from_edit)
        self.status_btn.clicked.connect(self._send_runtime_status)
        self.command_edit.returnPressed.connect(self._send_from_edit)
        self.ref_spin.valueChanged.connect(self._on_reference_spin_changed)
        self.ref_spin.editingFinished.connect(self._on_reference_editing_finished)
        self.ladrc_expect_spin.valueChanged.connect(self._on_ladrc_expect_spin_changed)
        self.ladrc_expect_spin.editingFinished.connect(self._on_reference_editing_finished)
        self.ladrc_r_spin.valueChanged.connect(self._on_ladrc_config_changed)
        self.ladrc_h_spin.valueChanged.connect(self._on_ladrc_config_changed)
        self.ladrc_w0_spin.valueChanged.connect(self._on_ladrc_config_changed)
        self.ladrc_wc_spin.valueChanged.connect(self._on_ladrc_config_changed)
        self.ladrc_b0_spin.valueChanged.connect(self._on_ladrc_config_changed)
        self.ladrc_init_spin.valueChanged.connect(self._on_ladrc_config_changed)
        self.ladrc_mode_combo.currentIndexChanged.connect(self._on_ladrc_config_changed)
        self.disturbance_combo.currentIndexChanged.connect(self._emit_disturbance_level)
        self.disturbance_mode_combo.currentIndexChanged.connect(self._emit_disturbance_mode)
        self.disturbance_amp_spin.valueChanged.connect(self._emit_disturbance_params)
        self.disturbance_freq_spin.valueChanged.connect(self._emit_disturbance_params)
        self.disturbance_bias_spin.valueChanged.connect(self._emit_disturbance_params)
        self.sim_period_spin.valueChanged.connect(self._on_sim_period_changed)
        self.simulated_upload_cb.toggled.connect(self.simulated_upload_changed.emit)
        self.ladrc_apply_config_btn.clicked.connect(self._apply_ladrc_config_now)
        self.ladrc_status_btn.clicked.connect(lambda: self._send_direct("#stat:1"))
        self.ladrc_flash_btn.clicked.connect(self._write_ladrc_flash)
        self.ladrc_start_btn.clicked.connect(self._start_selected_ladrc_mode)
        self.ladrc_idle_btn.clicked.connect(lambda: self._send_direct("#run:2"))
        self.ladrc_reset_btn.clicked.connect(self._reset_ladrc_runtime)
        self._bind_spinbox_return_pressed(self.ref_spin, self._commit_reference_input)
        self._bind_spinbox_return_pressed(self.ladrc_expect_spin, self._commit_reference_input)
        for widget in (
            self.ladrc_r_spin,
            self.ladrc_h_spin,
            self.ladrc_w0_spin,
            self.ladrc_wc_spin,
            self.ladrc_b0_spin,
        ):
            self._bind_spinbox_return_pressed(widget, self._commit_ladrc_param_input)
        self._bind_spinbox_return_pressed(self.ladrc_init_spin, self._commit_ladrc_target_input)
        default_algo_index = self.algo_combo.findData("LADRC")
        if default_algo_index >= 0:
            self.algo_combo.setCurrentIndex(default_algo_index)
        self._refresh_runtime_entry_visibility()

    def _apply_size_hints(self):
        metrics = self.fontMetrics()
        for button in (
            self.apply_algo_btn,
            self.set_ref_btn,
            self.run_btn,
            self.stop_btn,
            self.send_btn,
            self.status_btn,
            self.ladrc_apply_config_btn,
            self.ladrc_status_btn,
            self.ladrc_flash_btn,
            self.ladrc_start_btn,
            self.ladrc_idle_btn,
            self.ladrc_reset_btn,
        ):
            button.setMinimumWidth(metrics.horizontalAdvance(button.text()) + 10)
        for page in self._built_in_algorithm_pages.values():
            for button in (page.apply_btn, page.status_btn, page.flash_btn, page.start_btn, page.stop_btn, page.reset_btn):
                button.setMinimumWidth(metrics.horizontalAdvance(button.text()) + 10)

    def current_algorithm_key(self) -> str:
        return str(self.algo_combo.currentData() or "LADRC").strip()

    def current_algorithm_label(self) -> str:
        return self.algo_combo.currentText().strip() or self.current_algorithm_key()

    def is_custom_algorithm(self, algo_name: Optional[str] = None) -> bool:
        key = str(algo_name if algo_name is not None else self.current_algorithm_key()).strip()
        return key in self._custom_algorithm_pages

    def current_custom_algorithm_page(self) -> Optional[CustomAlgorithmPage]:
        return self._custom_algorithm_pages.get(self.current_algorithm_key())

    def current_algorithm_page(self) -> Optional[CustomAlgorithmPage]:
        algo_key = self.current_algorithm_key()
        page = self._built_in_algorithm_pages.get(algo_key)
        if page is not None:
            return page
        return self._custom_algorithm_pages.get(algo_key)

    def _rebuild_algorithm_page_indexes(self):
        self._algorithm_page_indexes = {
            "LADRC": self.algorithm_page_stack.indexOf(self.ladrc_page),
        }
        for algo_name, page in self._built_in_algorithm_pages.items():
            self._algorithm_page_indexes[algo_name] = self.algorithm_page_stack.indexOf(page)
        for algo_name, page in self._custom_algorithm_pages.items():
            self._algorithm_page_indexes[algo_name] = self.algorithm_page_stack.indexOf(page)

    def _stack_index_for_algorithm(self, algo_key: str) -> int:
        self._rebuild_algorithm_page_indexes()
        return self._algorithm_page_indexes.get(str(algo_key).strip(), 0)

    def apply_current_algorithm_set_command(self, command: str) -> bool:
        page = self.current_algorithm_page()
        if page is None:
            return False
        return page.apply_set_command(command)

    def _refresh_runtime_entry_visibility(self):
        algo_key = self.current_algorithm_key()
        ladrc_selected = str(algo_key).upper() == "LADRC"
        page_selected = algo_key in self._built_in_algorithm_pages or self.is_custom_algorithm(algo_key)
        if hasattr(self, "algorithm_badge_label"):
            self.algorithm_badge_label.setText(self.current_algorithm_label())
        self._refresh_command_edit_placeholder()
        for widget in (self.run_btn, self.stop_btn, self.status_btn):
            widget.setVisible(not ladrc_selected and not page_selected)
        self.ladrc_group.setVisible(ladrc_selected or page_selected)
        if ladrc_selected:
            self.ladrc_group.setTitle("LADRC 仿真")
            self.algorithm_page_stack.setCurrentIndex(self._stack_index_for_algorithm("LADRC"))
        elif page_selected:
            self.ladrc_group.setTitle(f"{self.current_algorithm_label()} 仿真")
            self.algorithm_page_stack.setCurrentIndex(self._stack_index_for_algorithm(algo_key))
        self._refresh_ladrc_dirty_state()

    def _toggle_ladrc_advanced_panel(self, expanded: bool):
        panel = getattr(self, "ladrc_advanced_panel", None)
        if panel is not None:
            panel.setVisible(bool(expanded))
        button = getattr(self, "ladrc_advanced_btn", None)
        if button is not None:
            button.setArrowType(QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow)

    def _create_ladrc_spin(self, minimum: float, maximum: float, decimals: int, step: float) -> QtWidgets.QDoubleSpinBox:
        spin = NoWheelDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        spin.setKeyboardTracking(False)
        spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        spin.setMinimumWidth(78)
        spin.setMaximumWidth(86)
        return spin

    def _bind_spinbox_return_pressed(self, widget, handler):
        line_edit = widget.lineEdit() if hasattr(widget, "lineEdit") else None
        if line_edit is not None:
            line_edit.returnPressed.connect(handler)

    def _is_ladrc_selected(self) -> bool:
        return self.current_algorithm_key().upper() == "LADRC"

    def _refresh_command_edit_placeholder(self):
        if not hasattr(self, "command_edit") or self.command_edit is None:
            return
        algo_key = self.current_algorithm_key().upper()
        if algo_key == "PID":
            placeholder = "输入命令，例如：#kp:1.2 或 #expe:1.5"
        elif algo_key == "LADRC":
            placeholder = "输入命令，例如：#wc:2.0 或 #stat:1"
        else:
            placeholder = "输入命令，例如：SET P 1.2 或 RUN 1"
        self.command_edit.setPlaceholderText(placeholder)

    def _set_current_algorithm(self, algo_name: str):
        index = self.algo_combo.findData(algo_name)
        if index >= 0:
            blocker = QtCore.QSignalBlocker(self.algo_combo)
            self.algo_combo.setCurrentIndex(index)
            del blocker
            self._refresh_runtime_entry_visibility()

    def custom_algorithms_state(self):
        return [
            self._custom_algorithm_pages[algo_name].definition_state()
            for algo_name in self._custom_algorithm_order
            if algo_name in self._custom_algorithm_pages
        ]

    def built_in_algorithm_state(self, algo_name: str) -> Optional[dict]:
        page = self._built_in_algorithm_pages.get(str(algo_name).strip())
        if page is None:
            return None
        return page.definition_state()

    def current_pid_config(self) -> dict:
        defaults = {
            str(item["command"]).strip().upper(): float(item.get("value", 0.0))
            for item in self.PID_DEFAULTS.get("parameters", [])
        }
        page_state = self.built_in_algorithm_state("PID") or {}
        for item in page_state.get("parameters", []):
            command_name = str(item.get("command", "")).strip().upper()
            if not command_name:
                continue
            try:
                defaults[command_name] = float(item.get("value", defaults.get(command_name, 0.0)))
            except (TypeError, ValueError):
                continue
        return defaults

    def apply_built_in_algorithm_state(self, algo_name: str, state: dict):
        page = self._built_in_algorithm_pages.get(str(algo_name).strip())
        if page is None or not isinstance(state, dict):
            return
        merged = page.definition_state()
        saved_values = {}
        for item in state.get("parameters", []):
            command_name = str(item.get("command", "")).strip().upper()
            if not command_name:
                continue
            try:
                saved_values[command_name] = float(item.get("value", 0.0))
            except (TypeError, ValueError):
                continue
        normalized_parameters = []
        for item in merged.get("parameters", []):
            normalized = dict(item)
            command_name = str(item.get("command", "")).strip().upper()
            if command_name in saved_values:
                normalized["value"] = saved_values[command_name]
            normalized_parameters.append(normalized)
        merged["parameters"] = normalized_parameters
        page.apply_definition(merged)
        page.mark_applied()

    def reset_built_in_algorithm_pages(self):
        for algo_name, page in self._built_in_algorithm_pages.items():
            if algo_name == "PID":
                page.apply_definition(self.PID_DEFAULTS)
                page.mark_applied()

    def clear_custom_algorithms(self, emit_signal: bool = True):
        blocker = QtCore.QSignalBlocker(self.algo_combo)
        for algo_name in list(self._custom_algorithm_order):
            page = self._custom_algorithm_pages.pop(algo_name, None)
            if page is not None:
                index = self.algo_combo.findData(algo_name)
                if index >= 0:
                    self.algo_combo.removeItem(index)
                self.algorithm_page_stack.removeWidget(page)
                page.deleteLater()
        self._custom_algorithm_order = []
        self._rebuild_algorithm_page_indexes()
        del blocker
        if self.algo_combo.findData("LADRC") >= 0:
            self._set_current_algorithm("LADRC")
        if emit_signal:
            self.algorithm_profiles_changed.emit()

    def register_custom_algorithm(self, definition: dict, select: bool = True, emit_signal: bool = True) -> bool:
        if not isinstance(definition, dict):
            return False
        algo_name = str(definition.get("name", "")).strip()
        if not algo_name:
            return False
        if algo_name.upper() in {"PID", "LADRC", "OPEN_LOOP"}:
            raise ValueError(f"算法名称不能使用保留字：{algo_name}")
        existing_names = {
            str(self.algo_combo.itemData(index) or "").strip().upper()
            for index in range(self.algo_combo.count())
        }
        if algo_name.upper() in existing_names:
            raise ValueError(f"算法名称已存在：{algo_name}")

        page = CustomAlgorithmPage(definition, self.algorithm_page_stack)
        page.send_command.connect(self._send_direct)
        metrics = self.fontMetrics()
        for button in (page.apply_btn, page.status_btn, page.flash_btn, page.start_btn, page.stop_btn, page.reset_btn):
            button.setMinimumWidth(metrics.horizontalAdvance(button.text()) + 12)
        self._custom_algorithm_pages[algo_name] = page
        self._custom_algorithm_order.append(algo_name)
        self.algorithm_page_stack.addWidget(page)
        self._rebuild_algorithm_page_indexes()
        self.algo_combo.addItem(algo_name, algo_name)
        if select:
            self._set_current_algorithm(algo_name)
        if emit_signal:
            self.algorithm_profiles_changed.emit()
        return True

    def open_new_algorithm_dialog(self, parent=None) -> Optional[str]:
        dialog = NewAlgorithmDialog(parent or self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return None
        definition = dialog.definition()
        if not isinstance(definition, dict):
            return None
        try:
            self.register_custom_algorithm(definition, select=True, emit_signal=True)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(parent or self, "新建失败", str(exc))
            return None
        return str(definition.get("name", "")).strip() or None

    def open_new_command_dialog(self, parent=None) -> Optional[str]:
        page = self.current_custom_algorithm_page()
        if page is None:
            QtWidgets.QMessageBox.information(parent or self, "无法新建命令", "请先切换到一个自定义算法页。")
            return None

        dialog = NewCommandDialog(page.algorithm_name(), parent or self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return None

        try:
            page.append_command_definitions(dialog.definitions())
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(parent or self, "新建失败", str(exc))
            return None

        self.algorithm_profiles_changed.emit()
        return page.algorithm_name()

    def remove_current_custom_algorithm(self) -> Optional[str]:
        algo_name = self.current_algorithm_key()
        page = self._custom_algorithm_pages.pop(algo_name, None)
        if page is None:
            return None

        if algo_name in self._custom_algorithm_order:
            self._custom_algorithm_order.remove(algo_name)

        combo_index = self.algo_combo.findData(algo_name)
        if combo_index >= 0:
            blocker = QtCore.QSignalBlocker(self.algo_combo)
            self.algo_combo.removeItem(combo_index)
            del blocker

        self.algorithm_page_stack.removeWidget(page)
        page.deleteLater()
        self._rebuild_algorithm_page_indexes()
        self._set_current_algorithm("LADRC")
        self.algorithm_profiles_changed.emit()
        return algo_name

    def current_custom_algorithm_has_commands(self) -> bool:
        page = self.current_custom_algorithm_page()
        return bool(page is not None and page.has_commands())

    def open_delete_command_dialog(self, parent=None) -> Optional[str]:
        page = self.current_custom_algorithm_page()
        if page is None:
            QtWidgets.QMessageBox.information(parent or self, "无法删除命令", "请先切换到一个自定义算法页。")
            return None
        if not page.has_commands():
            QtWidgets.QMessageBox.information(parent or self, "无法删除命令", "当前算法页还没有快捷命令。")
            return None

        dialog = DeleteCommandDialog(page.algorithm_name(), page.command_definitions(), parent or self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return None

        try:
            page.remove_command_labels(dialog.selected_labels())
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(parent or self, "删除失败", str(exc))
            return None

        self.algorithm_profiles_changed.emit()
        return page.algorithm_name()

    def _ladrc_applied_state(self) -> dict:
        return {
            "r": float(self.ladrc_r_spin.value()),
            "h": float(self.ladrc_h_spin.value()),
            "w0": float(self.ladrc_w0_spin.value()),
            "wc": float(self.ladrc_wc_spin.value()),
            "b0": float(self.ladrc_b0_spin.value()),
            "init": float(self.ladrc_init_spin.value()),
        }

    def _ladrc_applied_signature_from_state(self, state: Optional[dict] = None):
        source = state if isinstance(state, dict) else self._ladrc_applied_state()
        return tuple(
            self._normalize_ladrc_payload(source.get(key, 0.0))
            for key in ("r", "h", "w0", "wc", "b0", "init")
        )

    def _mark_ladrc_config_applied(self):
        self._ladrc_applied_signature = self._ladrc_applied_signature_from_state()
        self._refresh_ladrc_dirty_state()

    def _refresh_ladrc_dirty_state(self):
        current_signature = self._ladrc_applied_signature_from_state()
        dirty = self._ladrc_applied_signature is not None and current_signature != self._ladrc_applied_signature
        self.ladrc_dirty_label.setVisible(self._is_ladrc_selected() and dirty)

    def _set_spin_value(self, widget, value: float):
        blocker = QtCore.QSignalBlocker(widget)
        widget.setValue(float(value))
        del blocker

    def set_reference_value(self, value: float, sync_ladrc: bool = True):
        self._set_spin_value(self.ref_spin, float(value))
        if sync_ladrc:
            self._set_spin_value(self.ladrc_expect_spin, float(value))
        self._reference_dirty = False
        self._last_reference_edit_ms = 0

    def has_pending_reference_edit(self) -> bool:
        return bool(self._reference_dirty)

    def pending_reference_payload(self) -> Optional[str]:
        if not self._reference_dirty:
            return None
        return self._normalize_ladrc_payload(self.ref_spin.value())

    def is_reference_input_active(self) -> bool:
        widgets = (self.ref_spin, self.ladrc_expect_spin)
        for widget in widgets:
            if widget.hasFocus():
                return True
            line_edit = widget.lineEdit()
            if line_edit is not None and line_edit.hasFocus():
                return True
        if self._last_reference_edit_ms > 0 and (time.time() * 1000 - self._last_reference_edit_ms) < 1500:
            return True
        return False

    def _on_reference_spin_changed(self, value: float):
        self._last_reference_edit_ms = int(time.time() * 1000)
        self._reference_dirty = True
        if self._is_ladrc_selected():
            self._set_spin_value(self.ladrc_expect_spin, float(value))

    def _on_ladrc_expect_spin_changed(self, value: float):
        self._last_reference_edit_ms = int(time.time() * 1000)
        self._reference_dirty = True
        self._set_spin_value(self.ref_spin, float(value))

    def _on_ladrc_config_changed(self, *_args):
        self._refresh_ladrc_dirty_state()

    def _on_reference_editing_finished(self):
        sender = self.sender()
        widget = sender if sender in {self.ref_spin, self.ladrc_expect_spin} else None
        line_edit = widget.lineEdit() if widget is not None else None
        modified = bool(line_edit.isModified()) if line_edit is not None else False
        if widget is not None:
            self._interpret_spin_text(widget)
            if widget is self.ladrc_expect_spin:
                self._set_spin_value(self.ref_spin, float(self.ladrc_expect_spin.value()))
            elif widget is self.ref_spin and self._is_ladrc_selected():
                self._set_spin_value(self.ladrc_expect_spin, float(self.ref_spin.value()))
        if line_edit is not None:
            line_edit.setModified(False)
        if not self._reference_dirty and not modified:
            return
        self._reference_dirty = True
        self._last_reference_edit_ms = int(time.time() * 1000)
        self._commit_reference_input()

    def _interpret_spin_text(self, widget: QtWidgets.QDoubleSpinBox):
        try:
            widget.interpretText()
        except AttributeError:
            pass

    def _spinbox_triggered_by_sender(self, widgets):
        sender = self.sender()
        for widget in widgets:
            if sender is widget or sender is widget.lineEdit():
                return widget
        return None

    def _commit_reference_input(self):
        self._interpret_spin_text(self.ref_spin)
        self._interpret_spin_text(self.ladrc_expect_spin)
        self._send_ref()

    def _commit_ladrc_param_input(self):
        mapping = {
            self.ladrc_r_spin: ("r", "r"),
            self.ladrc_h_spin: ("h", "h"),
            self.ladrc_w0_spin: ("w0", "wo"),
            self.ladrc_wc_spin: ("wc", "wc"),
            self.ladrc_b0_spin: ("b0", "bo"),
        }
        widget = self._spinbox_triggered_by_sender(tuple(mapping.keys()))
        if widget is None:
            self._send_ladrc_param_commands(force=False)
            return
        self._interpret_spin_text(widget)
        key, command_type = mapping[widget]
        payload = self._format_ladrc_payload(widget.value())
        if self._ladrc_last_sent_payload.get(key) == payload:
            return
        self._send_direct(f"#{command_type}:{payload}")

    def _commit_ladrc_target_input(self):
        self._interpret_spin_text(self.ladrc_init_spin)
        payload = self._format_ladrc_payload(self.ladrc_init_spin.value())
        if self._ladrc_last_sent_payload.get("init") == payload:
            return
        self._send_direct(f"#init:{payload}")

    def _send_alg(self):
        algo = self.current_algorithm_key()
        self.algo_selected.emit(algo)
        if str(algo).strip().upper() == "PID":
            self._send_direct("#alg:PID")
            return
        self._send_direct(f"ALG {algo}")

    def current_protocol_start_command(self) -> str:
        if self.current_algorithm_key().strip().upper() in {"PID", "LADRC"}:
            return "#run:1"
        return "RUN 1"

    def current_protocol_stop_command(self) -> str:
        if self.current_algorithm_key().strip().upper() in {"PID", "LADRC"}:
            return "#run:2"
        return "RUN 0"

    def current_protocol_status_command(self) -> str:
        if self.current_algorithm_key().strip().upper() in {"PID", "LADRC"}:
            return "#stat:1"
        return "GET STATUS"

    def _send_runtime_start(self):
        self._send_direct(self.current_protocol_start_command())

    def _send_runtime_stop(self):
        self._send_direct(self.current_protocol_stop_command())

    def _send_runtime_status(self):
        self._send_direct(self.current_protocol_status_command())

    def _send_ref(self):
        value = self.ref_spin.value()
        self.ref_changed.emit(value)
        if self.current_algorithm_key().strip().upper() in {"PID", "LADRC"}:
            self.set_reference_value(value, sync_ladrc=True)
            self._send_direct(f"#expe:{self._format_ladrc_payload(value)}")
            return
        self._send_direct(f"SET REF {value:.3f}")

    def _send_direct(self, command: str):
        self.note_ladrc_command_sent(command)
        current_page = self.current_algorithm_page()
        if current_page is not None:
            current_page.note_command_sent(command)
        self.send_command.emit(command)
        self.append_console(f"> {command}")

    @staticmethod
    def _format_ladrc_payload(value: float) -> str:
        return _format_numeric_payload(value)

    @classmethod
    def _normalize_ladrc_payload(cls, payload: object) -> Optional[str]:
        return _normalize_numeric_payload(payload)

    @staticmethod
    def _parse_ladrc_command(command: str):
        raw = str(command).strip()
        if not raw.startswith("#") or ":" not in raw:
            return None, None
        cmd_type, payload = raw[1:].split(":", 1)
        cmd_type = cmd_type.strip().lower()
        payload = payload.strip()
        if not cmd_type or not payload:
            return None, None
        return cmd_type, payload

    def build_ladrc_commands(self, specs, force: bool = False, state: Optional[dict] = None):
        config = state if isinstance(state, dict) else self.current_ladrc_config()
        commands = []
        for key, command_type in specs:
            payload = self._format_ladrc_payload(config.get(key, 0.0))
            if not force and self._ladrc_last_sent_payload.get(key) == payload:
                continue
            commands.append(f"#{command_type}:{payload}")
        return commands

    def build_ladrc_param_commands(self, force: bool = False, state: Optional[dict] = None):
        return self.build_ladrc_commands(self.LADRC_PARAM_COMMANDS, force=force, state=state)

    def build_ladrc_target_commands(self, force: bool = False, state: Optional[dict] = None):
        return self.build_ladrc_commands(self.LADRC_TARGET_COMMANDS, force=force, state=state)

    def _send_ladrc_commands(self, specs, force: bool = False):
        for command in self.build_ladrc_commands(specs, force=force):
            self._send_direct(command)

    def _send_ladrc_param_commands(self, force: bool = True):
        self._send_ladrc_commands(self.LADRC_PARAM_COMMANDS, force=force)

    def _send_ladrc_target_commands(self, force: bool = True):
        self._send_ladrc_commands(self.LADRC_TARGET_COMMANDS, force=force)

    def _apply_ladrc_config_now(self):
        self._send_ladrc_param_commands(force=True)
        self._send_ladrc_target_commands(force=True)
        self._mark_ladrc_config_applied()

    def _write_ladrc_flash(self):
        self._send_ladrc_param_commands(force=True)
        self._send_ladrc_target_commands(force=True)
        self._send_direct("#save:1")
        self._mark_ladrc_config_applied()

    def current_ladrc_mode_value(self) -> int:
        current = self.ladrc_mode_combo.currentData()
        if current is None:
            current = self.LADRC_DEFAULTS["mode"]
        return int(current)

    def set_ladrc_mode_value(self, mode: int):
        target = int(mode)
        for index in range(self.ladrc_mode_combo.count()):
            if int(self.ladrc_mode_combo.itemData(index)) == target:
                blocker = QtCore.QSignalBlocker(self.ladrc_mode_combo)
                self.ladrc_mode_combo.setCurrentIndex(index)
                del blocker
                return

    def _start_selected_ladrc_mode(self):
        self._start_ladrc_mode(self.current_ladrc_mode_value())

    def _start_ladrc_mode(self, mode: int):
        commands = self.build_ladrc_param_commands(force=True)
        commands.extend(self.build_ladrc_target_commands(force=True))
        commands.append(f"#run:{int(mode)}")
        for command in commands:
            self._send_direct(command)
        self._mark_ladrc_config_applied()

    def _reset_ladrc_widgets(self):
        defaults = self.LADRC_DEFAULTS
        self.ladrc_r_spin.setValue(defaults["r"])
        self.ladrc_h_spin.setValue(defaults["h"])
        self.ladrc_w0_spin.setValue(defaults["w0"])
        self.ladrc_wc_spin.setValue(defaults["wc"])
        self.ladrc_b0_spin.setValue(defaults["b0"])
        self.ladrc_init_spin.setValue(defaults["init"])
        self.set_ladrc_mode_value(defaults["mode"])
        self.set_reference_value(defaults["expect"], sync_ladrc=True)

    def _reset_ladrc_runtime(self):
        self._reset_ladrc_widgets()
        self._send_direct("#rst:1")
        self._mark_ladrc_config_applied()

    def _emit_disturbance_level(self):
        self.disturbance_level_changed.emit(self.current_disturbance_key(), self.current_disturbance_scale())

    def _emit_disturbance_mode(self):
        self.disturbance_mode_changed.emit(self.current_disturbance_mode())

    def _emit_disturbance_params(self):
        params = self.current_disturbance_params()
        self.disturbance_params_changed.emit(
            float(params["amplitude_gain"]),
            float(params["frequency_gain"]),
            float(params["bias"]),
        )

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

    def current_disturbance_mode(self) -> str:
        data = self.disturbance_mode_combo.currentData()
        return str(data) if data else str(self.DISTURBANCE_DEFAULTS["mode"])

    def current_disturbance_params(self) -> dict:
        return {
            "amplitude_gain": float(self.disturbance_amp_spin.value()),
            "frequency_gain": float(self.disturbance_freq_spin.value()),
            "bias": float(self.disturbance_bias_spin.value()),
        }

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

    def set_disturbance_mode(self, mode_key: str, emit_signal: bool = False):
        target = str(mode_key).strip().lower()
        for index in range(self.disturbance_mode_combo.count()):
            data = self.disturbance_mode_combo.itemData(index)
            if str(data).strip().lower() == target:
                blocker = QtCore.QSignalBlocker(self.disturbance_mode_combo)
                self.disturbance_mode_combo.setCurrentIndex(index)
                del blocker
                if emit_signal:
                    self._emit_disturbance_mode()
                return

    def set_disturbance_params(self, params: Optional[dict] = None, emit_signal: bool = True):
        source = params if isinstance(params, dict) else self.DISTURBANCE_DEFAULTS
        blockers = [
            QtCore.QSignalBlocker(self.disturbance_amp_spin),
            QtCore.QSignalBlocker(self.disturbance_freq_spin),
            QtCore.QSignalBlocker(self.disturbance_bias_spin),
        ]
        try:
            self.disturbance_amp_spin.setValue(float(source.get("amplitude_gain", self.DISTURBANCE_DEFAULTS["amplitude_gain"])))
            self.disturbance_freq_spin.setValue(float(source.get("frequency_gain", self.DISTURBANCE_DEFAULTS["frequency_gain"])))
            self.disturbance_bias_spin.setValue(float(source.get("bias", self.DISTURBANCE_DEFAULTS["bias"])))
        finally:
            del blockers
        if emit_signal:
            self._emit_disturbance_params()

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
        text = f"{hz:.1f}".rstrip("0").rstrip(".")
        self.sim_rate_label.setText(f"{text}Hz")

    def get_state(self) -> dict:
        return {
            "algorithm": self.current_algorithm_key(),
            "reference": float(self.ref_spin.value()),
            "command_text": self.command_edit.text(),
            "disturbance_level": self.current_disturbance_key(),
            "disturbance_mode": self.current_disturbance_mode(),
            "disturbance_params": self.current_disturbance_params(),
            "sim_period_ms": self.current_sim_period_ms(),
            "simulated_upload": self.is_simulated_upload_enabled(),
            "ladrc": self.current_ladrc_config(),
            "pid": self.built_in_algorithm_state("PID"),
            "custom_algorithms": self.custom_algorithms_state(),
        }

    def apply_state(self, state: dict):
        if not isinstance(state, dict):
            return
        self.clear_custom_algorithms(emit_signal=False)
        custom_algorithms = state.get("custom_algorithms", [])
        if isinstance(custom_algorithms, list):
            for definition in custom_algorithms:
                try:
                    self.register_custom_algorithm(definition, select=False, emit_signal=False)
                except ValueError:
                    continue
        algo = state.get("algorithm")
        if algo is None:
            algo = "LADRC"
        self._set_current_algorithm(str(algo))
        if "reference" in state:
            try:
                self.set_reference_value(float(state.get("reference", 0.0)), sync_ladrc=True)
            except (TypeError, ValueError):
                pass
        if "command_text" in state:
            self.command_edit.setText(str(state.get("command_text", "")))
        if "disturbance_level" in state:
            self.set_disturbance_level(str(state.get("disturbance_level", "medium")))
        if "disturbance_mode" in state:
            self.set_disturbance_mode(str(state.get("disturbance_mode", self.DISTURBANCE_DEFAULTS["mode"])), emit_signal=False)
        if "disturbance_params" in state and isinstance(state.get("disturbance_params"), dict):
            self.set_disturbance_params(state.get("disturbance_params"), emit_signal=False)
        if "sim_period_ms" in state:
            try:
                self.set_sim_period_ms(int(state.get("sim_period_ms", 10)), emit_signal=False)
            except (TypeError, ValueError):
                self.set_sim_period_ms(10, emit_signal=False)
        if "simulated_upload" in state:
            self.set_simulated_upload_enabled(bool(state.get("simulated_upload")), emit_signal=True)
        pid_state = state.get("pid", {})
        if isinstance(pid_state, dict):
            self.apply_built_in_algorithm_state("PID", pid_state)
        ladrc_state = state.get("ladrc", {})
        if isinstance(ladrc_state, dict):
            self._apply_ladrc_state(ladrc_state)
            self._mark_ladrc_config_applied()
        self.clear_ladrc_sync_cache()
        self._refresh_runtime_entry_visibility()

    def reset_to_defaults(self):
        self.clear_custom_algorithms(emit_signal=False)
        self._set_current_algorithm("LADRC")
        self.set_reference_value(0.0, sync_ladrc=True)
        self.command_edit.clear()
        self.set_disturbance_level("medium")
        self.set_disturbance_mode(self.DISTURBANCE_DEFAULTS["mode"], emit_signal=False)
        self.set_disturbance_params(self.DISTURBANCE_DEFAULTS, emit_signal=True)
        self.set_sim_period_ms(10)
        self.set_simulated_upload_enabled(False)
        self.reset_built_in_algorithm_pages()
        self._reset_ladrc_widgets()
        self._mark_ladrc_config_applied()
        self.clear_ladrc_sync_cache()
        self.algorithm_profiles_changed.emit()

    def _raw_ladrc_config(self) -> dict:
        return {
            "r": float(self.ladrc_r_spin.value()),
            "h": float(self.ladrc_h_spin.value()),
            "w0": float(self.ladrc_w0_spin.value()),
            "wc": float(self.ladrc_wc_spin.value()),
            "b0": float(self.ladrc_b0_spin.value()),
            "init": float(self.ladrc_init_spin.value()),
            "expect": float(self.ref_spin.value()),
            "mode": self.current_ladrc_mode_value(),
        }

    def _should_use_safe_ladrc_profile(self, state: dict) -> bool:
        try:
            return (
                float(state.get("h", 0.0)) >= self.LADRC_UNSAFE_RUNTIME_LIMITS["h"]
                and float(state.get("w0", 0.0)) >= self.LADRC_UNSAFE_RUNTIME_LIMITS["w0"]
                and float(state.get("wc", 0.0)) >= self.LADRC_UNSAFE_RUNTIME_LIMITS["wc"]
                and float(state.get("b0", 0.0)) >= self.LADRC_UNSAFE_RUNTIME_LIMITS["b0"]
            )
        except (TypeError, ValueError):
            return True

    def current_ladrc_config(self, apply_runtime_safe: bool = False) -> dict:
        state = self._raw_ladrc_config()
        if self._should_use_safe_ladrc_profile(state):
            safe_state = dict(state)
            safe_state.update(
                {
                    "r": float(self.LADRC_DEFAULTS["r"]),
                    "h": float(self.LADRC_DEFAULTS["h"]),
                    "w0": float(self.LADRC_DEFAULTS["w0"]),
                    "wc": float(self.LADRC_DEFAULTS["wc"]),
                    "b0": float(self.LADRC_DEFAULTS["b0"]),
                }
            )
            if apply_runtime_safe:
                self._apply_ladrc_state(safe_state)
            return safe_state
        return state

    def apply_ladrc_config(self, state: dict):
        self._apply_ladrc_state(state)

    def apply_ladrc_runtime_state(self, state: dict):
        if not isinstance(state, dict):
            return
        mapping = {
            "r": self.ladrc_r_spin,
            "h": self.ladrc_h_spin,
            "w0": self.ladrc_w0_spin,
            "wc": self.ladrc_wc_spin,
            "b0": self.ladrc_b0_spin,
            "init": self.ladrc_init_spin,
        }
        for key, widget in mapping.items():
            if key not in state:
                continue
            try:
                widget.setValue(float(state[key]))
            except (TypeError, ValueError):
                continue
        self._refresh_ladrc_dirty_state()

    def reset_ladrc_config(self):
        self._reset_ladrc_widgets()
        self._mark_ladrc_config_applied()

    def clear_ladrc_sync_cache(self):
        self._ladrc_last_sent_payload.clear()

    def sync_ladrc_sent_cache(self, state: Optional[dict] = None):
        source = state if isinstance(state, dict) else self.current_ladrc_config()
        for key, _ in self.LADRC_PARAM_COMMANDS + self.LADRC_TARGET_COMMANDS:
            if key not in source:
                continue
            payload = self._normalize_ladrc_payload(source[key])
            if payload is None:
                continue
            self._ladrc_last_sent_payload[key] = payload

    def note_ladrc_command_sent(self, command: str):
        cmd_type, payload = self._parse_ladrc_command(command)
        if not cmd_type:
            return
        if cmd_type == "rst":
            try:
                if int(float(payload)):
                    self.sync_ladrc_sent_cache(self.LADRC_DEFAULTS)
            except (TypeError, ValueError):
                pass
            return

        mapping = {
            "r": "r",
            "h": "h",
            "wo": "w0",
            "wc": "wc",
            "bo": "b0",
            "init": "init",
            "expe": "expect",
        }
        key = mapping.get(cmd_type)
        if key is None:
            return
        normalized_payload = self._normalize_ladrc_payload(payload)
        if normalized_payload is None:
            return
        self._ladrc_last_sent_payload[key] = normalized_payload

    def _apply_ladrc_state(self, state: dict):
        defaults = self.LADRC_DEFAULTS
        fields = (
            ("r", self.ladrc_r_spin),
            ("h", self.ladrc_h_spin),
            ("w0", self.ladrc_w0_spin),
            ("wc", self.ladrc_wc_spin),
            ("b0", self.ladrc_b0_spin),
            ("init", self.ladrc_init_spin),
            ("expect", self.ladrc_expect_spin),
        )
        for key, widget in fields:
            if key == "expect":
                try:
                    self.set_reference_value(float(state.get(key, defaults[key])), sync_ladrc=True)
                except (TypeError, ValueError):
                    self.set_reference_value(defaults[key], sync_ladrc=True)
                continue
            try:
                widget.setValue(float(state.get(key, defaults[key])))
            except (TypeError, ValueError):
                widget.setValue(defaults[key])
        try:
            self.set_ladrc_mode_value(int(state.get("mode", defaults["mode"])))
        except (TypeError, ValueError):
            self.set_ladrc_mode_value(int(defaults["mode"]))
        self._refresh_ladrc_dirty_state()
