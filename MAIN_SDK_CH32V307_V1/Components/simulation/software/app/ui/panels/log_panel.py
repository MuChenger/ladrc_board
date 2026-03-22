from PyQt5 import QtCore, QtWidgets


class LogPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._title_bar_detached = False
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.copy_action = QtWidgets.QAction("复制全部", self)
        self.copy_action.triggered.connect(self._copy_all)

        self.clear_action = QtWidgets.QAction("清空日志", self)
        self.clear_action.triggered.connect(self._clear_console)

        self._title_bar = QtWidgets.QWidget()
        self._title_bar.setObjectName("dockTitleBar")
        title_layout = QtWidgets.QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(10, 4, 8, 4)
        title_layout.setSpacing(6)

        self.title_label = QtWidgets.QLabel("控制台")
        self.title_label.setObjectName("dockTitleText")

        self.count_label = QtWidgets.QLabel("0 行")
        self.count_label.setObjectName("statusHint")

        self.actions_btn = QtWidgets.QToolButton()
        self.actions_btn.setObjectName("dockTitleAction")
        self.actions_btn.setText("操作")
        self.actions_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.actions_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.actions_btn.setAutoRaise(False)

        actions_menu = QtWidgets.QMenu(self.actions_btn)
        actions_menu.addAction(self.copy_action)
        actions_menu.addAction(self.clear_action)
        self.actions_btn.setMenu(actions_menu)

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.count_label)
        title_layout.addStretch(1)
        title_layout.addWidget(self.actions_btn)

        self.console = QtWidgets.QPlainTextEdit()
        self.console.setObjectName("consoleView")
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(1500)
        self.console.setPlaceholderText("命令回显、串口日志和错误信息会显示在这里。")
        self.console.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        layout.addWidget(self.console, 1)

        self.console.customContextMenuRequested.connect(self._show_context_menu)

    def take_title_bar_widget(self) -> QtWidgets.QWidget:
        self._title_bar_detached = True
        return self._title_bar

    def _clear_console(self):
        self.console.clear()
        self._update_line_count()

    def _copy_all(self):
        QtWidgets.QApplication.clipboard().setText(self.console.toPlainText())

    def append_line(self, line: str):
        self.console.appendPlainText(line)
        self._update_line_count()

    def _update_line_count(self):
        block_count = max(0, self.console.document().blockCount())
        if not self.console.toPlainText().strip():
            block_count = 0
        self.count_label.setText(f"{block_count} 行")

    def _show_context_menu(self, pos):
        menu = self.console.createStandardContextMenu()
        menu.addSeparator()
        menu.addAction(self.copy_action)
        menu.addAction(self.clear_action)
        menu.exec_(self.console.mapToGlobal(pos))
