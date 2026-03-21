from PyQt5 import QtCore, QtWidgets


class StatusPanel(QtWidgets.QWidget):
    MODEL_CONTEXT = {
        "rov": ("仿真深度", "深度变化率", "环境扰动"),
        "aircraft": ("仿真高度", "高度变化率", "气流扰动"),
        "generic": ("垂向位置", "垂向速度", "外部扰动"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self.set_model_context("rov")

    def _build(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self.control_card, control_grid = self._create_card("控制状态")
        self.vertical_card, vertical_grid = self._create_card("垂向仿真")
        self.comm_card, comm_grid = self._create_card("通信状态")

        self.algo_val = self._value_label("PID")
        self.run_val = self._value_label("空闲")
        self.ref_val = self._value_label("0.000")
        self.feedback_val = self._value_label("0.000")
        self.u_val = self._value_label("0.000")

        self.vertical_val = self._value_label("0.000")
        self.vertical_rate_val = self._value_label("0.000")
        self.disturbance_val = self._value_label("0.000")

        self.rx_val = self._value_label("0")
        self.tx_val = self._value_label("0")
        self.err_val = self._value_label("0")
        self.lat_val = self._value_label("0 ms")
        self.timeout_val = self._value_label("正常")

        self.feedback_key_label = self._key_label("控制反馈")
        self.vertical_key_label = self._key_label("仿真深度")
        self.vertical_rate_key_label = self._key_label("深度变化率")
        self.disturbance_key_label = self._key_label("环境扰动")

        self._add_rows(
            control_grid,
            [
                ("算法", self.algo_val),
                ("运行状态", self.run_val),
                ("参考值", self.ref_val),
                (self.feedback_key_label, self.feedback_val),
                ("控制输出", self.u_val),
            ],
        )
        self._add_rows(
            vertical_grid,
            [
                (self.vertical_key_label, self.vertical_val),
                (self.vertical_rate_key_label, self.vertical_rate_val),
                (self.disturbance_key_label, self.disturbance_val),
            ],
        )
        self._add_rows(
            comm_grid,
            [
                ("接收帧数", self.rx_val),
                ("发送帧数", self.tx_val),
                ("解析错误", self.err_val),
                ("延迟", self.lat_val),
                ("通信状态", self.timeout_val),
            ],
        )

        root.addWidget(self.control_card)
        root.addWidget(self.vertical_card)
        root.addWidget(self.comm_card)
        root.addStretch(1)

    def _create_card(self, title: str):
        card = QtWidgets.QGroupBox(title)
        grid = QtWidgets.QGridLayout(card)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(7)
        grid.setColumnStretch(1, 1)
        return card, grid

    def _key_label(self, text: str):
        label = QtWidgets.QLabel(text)
        label.setProperty("statusKey", True)
        return label

    def _value_label(self, text: str):
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        label.setProperty("statusValue", True)
        return label

    def _add_rows(self, grid: QtWidgets.QGridLayout, rows):
        for row_index, (key, value) in enumerate(rows):
            key_widget = key if isinstance(key, QtWidgets.QWidget) else self._key_label(key)
            value_widget = value if isinstance(value, QtWidgets.QWidget) else self._value_label(str(value))
            grid.addWidget(key_widget, row_index, 0)
            grid.addWidget(value_widget, row_index, 1)

    def set_model_context(self, model_type: str):
        vertical_label, vertical_rate_label, disturbance_label = self.MODEL_CONTEXT.get(
            model_type,
            self.MODEL_CONTEXT["rov"],
        )
        self.feedback_key_label.setText("控制反馈")
        self.vertical_key_label.setText(vertical_label)
        self.vertical_rate_key_label.setText(vertical_rate_label)
        self.disturbance_key_label.setText(disturbance_label)

    def update_control(self, algo: str, run_state: int, ref: float, feedback: float, u_cmd: float):
        self.algo_val.setText(algo)
        self.run_val.setText("运行中" if run_state else "空闲")
        self.ref_val.setText(f"{ref:.3f}")
        self.feedback_val.setText(f"{feedback:.3f}")
        self.u_val.setText(f"{u_cmd:.3f}")

    def update_vertical_state(self, vertical: float, vertical_rate: float, disturbance: float):
        self.vertical_val.setText(f"{vertical:.3f}")
        self.vertical_rate_val.setText(f"{vertical_rate:.3f}")
        self.disturbance_val.setText(f"{disturbance:.3f}")

    def update_comm(self, rx_frames: int, tx_frames: int, parse_errors: int, latency_ms: int):
        self.rx_val.setText(str(rx_frames))
        self.tx_val.setText(str(tx_frames))
        self.err_val.setText(str(parse_errors))
        self.lat_val.setText(f"{latency_ms} ms")

    def set_timeout(self, timeout: bool):
        self.timeout_val.setText("超时" if timeout else "正常")
