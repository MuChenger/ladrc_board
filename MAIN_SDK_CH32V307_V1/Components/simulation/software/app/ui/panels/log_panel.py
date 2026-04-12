from collections import deque

from PyQt5 import QtCore, QtWidgets


class LogPanel(QtWidgets.QWidget):
    DIRECTION_SYSTEM = "system"
    DIRECTION_TX = "tx"
    DIRECTION_RX = "rx"

    FILTER_ALL = "all"
    FILTER_TX = "tx"
    FILTER_RX = "rx"

    _MAX_ENTRIES = 1500

    expand_requested = QtCore.pyqtSignal()
    hide_requested = QtCore.pyqtSignal()
    close_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("logPanel")
        self._title_bar_detached = False
        self._auto_follow = True
        self._suspend_scroll_tracking = False
        self._entries = deque()
        self._filter_mode = self.FILTER_ALL
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.copy_action = QtWidgets.QAction("复制全部", self)
        self.copy_action.triggered.connect(self._copy_all)

        self.clear_action = QtWidgets.QAction("清空日志", self)
        self.clear_action.triggered.connect(self._clear_console)

        self._title_bar = QtWidgets.QWidget()
        self._title_bar.setObjectName("panelHero")
        title_layout = QtWidgets.QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(14, 10, 14, 10)
        title_layout.setSpacing(8)

        self.title_label = QtWidgets.QLabel("控制台")
        self.title_label.setObjectName("panelHeroTitle")

        self.count_label = QtWidgets.QLabel("0 行")
        self.count_label.setObjectName("panelSummary")

        self.filter_label = QtWidgets.QLabel("显示")
        self.filter_label.setObjectName("panelFieldLabel")

        self._filter_buttons = {}
        self.filter_all_btn = self._create_filter_button("全部", self.FILTER_ALL, "同时显示 TX / RX 和系统日志")
        self.filter_tx_btn = self._create_filter_button("TX", self.FILTER_TX, "仅显示上位机发出的 TX 日志")
        self.filter_rx_btn = self._create_filter_button("RX", self.FILTER_RX, "仅显示下位机返回的 RX 日志")

        self.actions_btn = QtWidgets.QToolButton()
        self.actions_btn.setObjectName("dockTitleAction")
        self.actions_btn.setProperty("secondaryRole", True)
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
        self.expand_btn.setProperty("accentRole", True)
        self.expand_btn.setText("放大")
        self.expand_btn.setToolTip("放大控制台")
        self.expand_btn.clicked.connect(self.expand_requested.emit)

        self.hide_btn = QtWidgets.QToolButton()
        self.hide_btn.setObjectName("dockTitleAction")
        self.hide_btn.setProperty("secondaryRole", True)
        self.hide_btn.setText("隐藏")
        self.hide_btn.setToolTip("隐藏控制台")
        self.hide_btn.clicked.connect(self.hide_requested.emit)

        self.close_btn = QtWidgets.QToolButton()
        self.close_btn.setObjectName("dockTitleAction")
        self.close_btn.setProperty("dangerRole", True)
        self.close_btn.setText("关闭")
        self.close_btn.setToolTip("关闭控制台")
        self.close_btn.clicked.connect(self.close_requested.emit)

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.count_label)
        title_layout.addStretch(1)
        title_layout.addWidget(self.filter_label)
        title_layout.addWidget(self.filter_all_btn)
        title_layout.addWidget(self.filter_tx_btn)
        title_layout.addWidget(self.filter_rx_btn)
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

        console_card = QtWidgets.QFrame()
        console_card.setObjectName("panelCard")
        console_layout = QtWidgets.QVBoxLayout(console_card)
        console_layout.setContentsMargins(12, 12, 12, 12)
        console_layout.setSpacing(0)
        console_layout.addWidget(self.console, 1)

        layout.addWidget(console_card, 1)

        self.console.customContextMenuRequested.connect(self._show_context_menu)
        self._sync_filter_buttons()
        self._update_line_count()

    def take_title_bar_widget(self) -> QtWidgets.QWidget:
        self._title_bar_detached = True
        return self._title_bar

    def _create_filter_button(self, text: str, mode: str, tooltip: str) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton()
        button.setObjectName("dockTitleAction")
        button.setProperty("secondaryRole", True)
        button.setText(text)
        button.setToolTip(tooltip)
        button.setCheckable(True)
        button.setAutoRaise(False)
        button.clicked.connect(lambda _checked=False, value=mode: self.set_filter_mode(value))
        self._filter_buttons[mode] = button
        return button

    def _clear_console(self):
        self._entries.clear()
        self.console.clear()
        self._auto_follow = True
        self._update_line_count()
        QtCore.QTimer.singleShot(0, self._scroll_to_bottom)

    def _copy_all(self):
        QtWidgets.QApplication.clipboard().setText(self.console.toPlainText())

    def append_line(self, line: str, direction: str = DIRECTION_SYSTEM):
        line = str(line)
        direction = self._normalize_direction(direction)
        evicted = None
        if len(self._entries) >= self._MAX_ENTRIES:
            evicted = self._entries.popleft()
        self._entries.append((line, direction))
        if evicted is not None:
            self._rebuild_console()
            return
        if not self._matches_filter(direction):
            self._update_line_count()
            return
        scrollbar = self.console.verticalScrollBar()
        previous_value = scrollbar.value()
        self.console.appendPlainText(line)
        self._update_line_count()
        if self._auto_follow:
            QtCore.QTimer.singleShot(0, self._scroll_to_bottom)
        else:
            QtCore.QTimer.singleShot(0, lambda value=previous_value: self._restore_scroll_position(value))

    def get_state(self) -> dict:
        return {"filter": self._filter_mode}

    def apply_state(self, state: dict):
        if not isinstance(state, dict):
            return
        self.set_filter_mode(str(state.get("filter", self.FILTER_ALL)).strip().lower())

    def reset_to_defaults(self):
        self.set_filter_mode(self.FILTER_ALL)

    def set_filter_mode(self, mode: str):
        mode = str(mode or "").strip().lower()
        if mode not in self._filter_buttons:
            mode = self.FILTER_ALL
        if self._filter_mode == mode:
            self._sync_filter_buttons()
            self._update_line_count()
            return
        self._filter_mode = mode
        self._sync_filter_buttons()
        self._rebuild_console()

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
        total_count = len(self._entries)
        visible_count = sum(1 for _line, direction in self._entries if self._matches_filter(direction))
        if self._filter_mode == self.FILTER_ALL:
            self.count_label.setText(f"{visible_count} 行")
        else:
            self.count_label.setText(f"{visible_count} / {total_count} 行")

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

    def _normalize_direction(self, direction: str) -> str:
        direction = str(direction or "").strip().lower()
        if direction in (self.DIRECTION_TX, self.DIRECTION_RX):
            return direction
        return self.DIRECTION_SYSTEM

    def _matches_filter(self, direction: str) -> bool:
        if self._filter_mode == self.FILTER_TX:
            return direction == self.DIRECTION_TX
        if self._filter_mode == self.FILTER_RX:
            return direction == self.DIRECTION_RX
        return True

    def _sync_filter_buttons(self):
        for mode, button in self._filter_buttons.items():
            blocker = QtCore.QSignalBlocker(button)
            button.setChecked(mode == self._filter_mode)
            del blocker

    def _rebuild_console(self):
        visible_lines = [line for line, direction in self._entries if self._matches_filter(direction)]
        scrollbar = self.console.verticalScrollBar()
        previous_value = scrollbar.value()
        self.console.setUpdatesEnabled(False)
        try:
            self.console.setPlainText("\n".join(visible_lines))
        finally:
            self.console.setUpdatesEnabled(True)
        self._update_line_count()
        if self._auto_follow:
            QtCore.QTimer.singleShot(0, self._scroll_to_bottom)
        else:
            QtCore.QTimer.singleShot(0, lambda value=previous_value: self._restore_scroll_position(value))
