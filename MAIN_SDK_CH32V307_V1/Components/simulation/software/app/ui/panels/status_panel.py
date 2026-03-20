from PyQt5 import QtWidgets


class StatusPanel(QtWidgets.QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Runtime Status", parent)
        self._build()

    def _build(self):
        grid = QtWidgets.QGridLayout(self)
        self.algo_val = QtWidgets.QLabel("N/A")
        self.run_val = QtWidgets.QLabel("IDLE")
        self.ref_val = QtWidgets.QLabel("0.000")
        self.feedback_val = QtWidgets.QLabel("0.000")
        self.u_val = QtWidgets.QLabel("0.000")
        self.rx_val = QtWidgets.QLabel("0")
        self.tx_val = QtWidgets.QLabel("0")
        self.err_val = QtWidgets.QLabel("0")
        self.lat_val = QtWidgets.QLabel("0 ms")
        self.timeout_val = QtWidgets.QLabel("OK")

        rows = [
            ("Algorithm", self.algo_val),
            ("Run State", self.run_val),
            ("Ref", self.ref_val),
            ("Feedback", self.feedback_val),
            ("u_cmd", self.u_val),
            ("RX Frames", self.rx_val),
            ("TX Frames", self.tx_val),
            ("Parse Errors", self.err_val),
            ("Latency", self.lat_val),
            ("Comm Timeout", self.timeout_val),
        ]
        for r, (k, v) in enumerate(rows):
            grid.addWidget(QtWidgets.QLabel(k), r, 0)
            grid.addWidget(v, r, 1)

    def update_control(self, algo: str, run_state: int, ref: float, feedback: float, u_cmd: float):
        self.algo_val.setText(algo)
        self.run_val.setText("RUN" if run_state else "IDLE")
        self.ref_val.setText(f"{ref:.3f}")
        self.feedback_val.setText(f"{feedback:.3f}")
        self.u_val.setText(f"{u_cmd:.3f}")

    def update_comm(self, rx_frames: int, tx_frames: int, parse_errors: int, latency_ms: int):
        self.rx_val.setText(str(rx_frames))
        self.tx_val.setText(str(tx_frames))
        self.err_val.setText(str(parse_errors))
        self.lat_val.setText(f"{latency_ms} ms")

    def set_timeout(self, timeout: bool):
        self.timeout_val.setText("TIMEOUT" if timeout else "OK")

