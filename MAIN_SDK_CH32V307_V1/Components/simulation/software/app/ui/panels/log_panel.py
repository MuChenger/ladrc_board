from PyQt5 import QtWidgets


class LogPanel(QtWidgets.QGroupBox):
    def __init__(self, parent=None):
        super().__init__("日志输出", parent)
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        toolbar = QtWidgets.QHBoxLayout()
        self.clear_btn = QtWidgets.QPushButton("清空日志")
        self.copy_btn = QtWidgets.QPushButton("复制全部")
        toolbar.addWidget(self.clear_btn)
        toolbar.addWidget(self.copy_btn)
        toolbar.addStretch(1)

        self.console = QtWidgets.QPlainTextEdit()
        self.console.setObjectName("consoleView")
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(1500)
        self.console.setPlaceholderText("命令回显、串口日志和错误信息会显示在这里。")

        layout.addLayout(toolbar)
        layout.addWidget(self.console, 1)

        self.clear_btn.clicked.connect(self.console.clear)
        self.copy_btn.clicked.connect(self._copy_all)

    def _copy_all(self):
        QtWidgets.QApplication.clipboard().setText(self.console.toPlainText())

    def append_line(self, line: str):
        self.console.appendPlainText(line)
