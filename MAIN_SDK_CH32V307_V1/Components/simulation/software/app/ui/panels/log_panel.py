from PyQt5 import QtCore, QtWidgets


class LogPanel(QtWidgets.QWidget):
    expand_requested = QtCore.pyqtSignal()
    hide_requested = QtCore.pyqtSignal()
    close_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._title_bar_detached = False
        self._auto_follow = True
        self._suspend_scroll_tracking = False
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

        self.expand_btn = QtWidgets.QToolButton()
        self.expand_btn.setObjectName("dockTitleAction")
        self.expand_btn.setText("放大")
        self.expand_btn.setToolTip("放大控制台")
        self.expand_btn.clicked.connect(self.expand_requested.emit)

        self.hide_btn = QtWidgets.QToolButton()
        self.hide_btn.setObjectName("dockTitleAction")
        self.hide_btn.setText("隐藏")
        self.hide_btn.setToolTip("隐藏控制台")
        self.hide_btn.clicked.connect(self.hide_requested.emit)

        self.close_btn = QtWidgets.QToolButton()
        self.close_btn.setObjectName("dockTitleAction")
        self.close_btn.setText("关闭")
        self.close_btn.setToolTip("关闭控制台")
        self.close_btn.clicked.connect(self.close_requested.emit)

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.count_label)
        title_layout.addStretch(1)
        title_layout.addWidget(self.expand_btn)
        title_layout.addWidget(self.hide_btn)
        title_layout.addWidget(self.close_btn)
        title_layout.addWidget(self.actions_btn)

        self.console = QtWidgets.QPlainTextEdit()
        self.console.setObjectName("consoleView")
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(1500)
        self.console.setPlaceholderText("下位机上行数据、上位机下行数据和错误信息会显示在这里。")
        self.console.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.console.verticalScrollBar().valueChanged.connect(self._on_scroll_value_changed)
        self.console.verticalScrollBar().rangeChanged.connect(self._on_scroll_range_changed)

        layout.addWidget(self.console, 1)

        self.console.customContextMenuRequested.connect(self._show_context_menu)

    def take_title_bar_widget(self) -> QtWidgets.QWidget:
        self._title_bar_detached = True
        return self._title_bar

    def _clear_console(self):
        self.console.clear()
        self._auto_follow = True
        self._update_line_count()
        QtCore.QTimer.singleShot(0, self._scroll_to_bottom)

    def _copy_all(self):
        QtWidgets.QApplication.clipboard().setText(self.console.toPlainText())

    def append_line(self, line: str):
        scrollbar = self.console.verticalScrollBar()
        previous_value = scrollbar.value()
        self.console.appendPlainText(line)
        self._update_line_count()
        if self._auto_follow:
            QtCore.QTimer.singleShot(0, self._scroll_to_bottom)
        else:
            QtCore.QTimer.singleShot(0, lambda value=previous_value: self._restore_scroll_position(value))

    def set_expanded(self, expanded: bool):
        if expanded:
            self.expand_btn.setText("还原")
            self.expand_btn.setToolTip("还原为底部嵌入样式")
            self.close_btn.setEnabled(True)
            self.close_btn.setToolTip("关闭放大视图并还原为底部嵌入样式")
        else:
            self.expand_btn.setText("放大")
            self.expand_btn.setToolTip("放大控制台")
            self.close_btn.setEnabled(False)
            self.close_btn.setToolTip("仅在放大视图下可用，用于还原为底部嵌入样式")

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

    def _scroll_to_bottom(self):
        scrollbar = self.console.verticalScrollBar()
        self._auto_follow = True
        self._suspend_scroll_tracking = True
        try:
            scrollbar.setValue(scrollbar.maximum())
        finally:
            self._suspend_scroll_tracking = False

    def _restore_scroll_position(self, value: int):
        scrollbar = self.console.verticalScrollBar()
        self._suspend_scroll_tracking = True
        try:
            value = max(scrollbar.minimum(), min(int(value), scrollbar.maximum()))
            scrollbar.setValue(value)
        finally:
            self._suspend_scroll_tracking = False

    def _on_scroll_value_changed(self, value: int):
        if self._suspend_scroll_tracking:
            return
        scrollbar = self.console.verticalScrollBar()
        self._auto_follow = value >= max(scrollbar.minimum(), scrollbar.maximum() - 2)

    def _on_scroll_range_changed(self, _minimum: int, _maximum: int):
        if self._auto_follow:
            self._scroll_to_bottom()
