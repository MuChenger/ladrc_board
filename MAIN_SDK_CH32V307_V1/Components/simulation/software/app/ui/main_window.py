import sys
import time
from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from ..config import DEFAULT_CONFIG
from ..core.protocol import telemetry_to_record_dict
from ..core.recorder import CsvRecorder
from ..core.serial_worker import SerialWorker
from ..core.simulator import DepthPlantSimulator
from ..core.models import SimFeedback, Telemetry
from .panels.command_panel import CommandPanel
from .panels.plot_panel import PlotPanel
from .panels.serial_panel import SerialPanel
from .panels.status_panel import StatusPanel


ALGO_NAME = {0: "PID", 1: "LADRC", 2: "OPEN_LOOP"}


class MainWindow(QtWidgets.QMainWindow):
    send_line_signal = QtCore.pyqtSignal(str)
    send_feedback_signal = QtCore.pyqtSignal(object)
    open_serial_signal = QtCore.pyqtSignal(str, int)
    close_serial_signal = QtCore.pyqtSignal()
    set_binary_signal = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.cfg = DEFAULT_CONFIG
        self.setWindowTitle(self.cfg.app_name)
        self.resize(1400, 860)

        self._latest_telemetry = Telemetry()
        self._latest_feedback = SimFeedback(timestamp_ms=0, depth=0.0, depth_rate=0.0, disturbance=0.0)
        self._start_monotonic = time.monotonic()
        self._last_serial_tx = 0.0
        self._last_rx_ms = 0

        self.recorder = CsvRecorder()
        self.sim = DepthPlantSimulator()

        self._build_ui()
        self._setup_worker()
        self._setup_timers()
        self._refresh_ports()

    def closeEvent(self, event):
        self.close_serial_signal.emit()
        self.worker_thread.quit()
        self.worker_thread.wait(1000)
        self.recorder.stop()
        super().closeEvent(event)

    def _build_ui(self):
        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        layout = QtWidgets.QHBoxLayout(root)

        left = QtWidgets.QVBoxLayout()
        self.serial_panel = SerialPanel()
        self.command_panel = CommandPanel()
        self.status_panel = StatusPanel()
        self.record_btn = QtWidgets.QPushButton("Start Record")
        self.record_path_label = QtWidgets.QLabel("No record file")
        left.addWidget(self.serial_panel)
        left.addWidget(self.command_panel, 1)
        left.addWidget(self.status_panel)
        left.addWidget(self.record_btn)
        left.addWidget(self.record_path_label)
        left.addStretch(1)

        right = QtWidgets.QVBoxLayout()
        self.plot_panel = PlotPanel(window_sec=self.cfg.plot_window_sec)
        right.addWidget(self.plot_panel, 1)

        layout.addLayout(left, 0)
        layout.addLayout(right, 1)

        self.serial_panel.refresh_requested.connect(self._refresh_ports)
        self.serial_panel.connect_requested.connect(self.open_serial_signal.emit)
        self.serial_panel.disconnect_requested.connect(self.close_serial_signal.emit)
        self.serial_panel.binary_tx_changed.connect(self.set_binary_signal.emit)

        self.command_panel.send_command.connect(self._send_command)
        self.record_btn.clicked.connect(self._toggle_record)

    def _setup_worker(self):
        self.worker_thread = QtCore.QThread(self)
        self.worker = SerialWorker(use_binary_tx=True)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        self.open_serial_signal.connect(self.worker.open)
        self.close_serial_signal.connect(self.worker.close)
        self.send_line_signal.connect(self.worker.send_line)
        self.send_feedback_signal.connect(self.worker.send_feedback)
        self.set_binary_signal.connect(self.worker.set_binary_tx)

        self.worker.telemetry_received.connect(self._on_telemetry)
        self.worker.line_received.connect(self._on_line)
        self.worker.comm_stats.connect(self._on_stats)
        self.worker.connection_changed.connect(self._on_connection_changed)
        self.worker.error.connect(self._append_log_error)

    def _setup_timers(self):
        self.sim_timer = QtCore.QTimer(self)
        self.sim_timer.setInterval(int(1000 / self.cfg.sim_hz))
        self.sim_timer.timeout.connect(self._on_sim_tick)
        self.sim_timer.start()

        self.ui_timer = QtCore.QTimer(self)
        self.ui_timer.setInterval(int(1000 / self.cfg.ui_refresh_hz))
        self.ui_timer.timeout.connect(self._update_timeout_state)
        self.ui_timer.start()

        self._last_sim_time = time.monotonic()

    def _refresh_ports(self):
        ports = SerialWorker.list_ports()
        self.serial_panel.set_ports(ports)

    def _send_command(self, command: str):
        self.send_line_signal.emit(command)

    def _toggle_record(self):
        if self.recorder.active:
            self.recorder.stop()
            self.record_btn.setText("Start Record")
            self.record_path_label.setText("Record stopped")
            return

        default_name = f"log_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        target, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save CSV",
            str(Path.cwd() / default_name),
            "CSV Files (*.csv)",
        )
        if not target:
            return
        self.recorder.start(Path(target))
        self.record_btn.setText("Stop Record")
        self.record_path_label.setText(target)
        self.command_panel.append_console(f"[record] start -> {target}")

    def _on_connection_changed(self, connected: bool, desc: str):
        self.serial_panel.set_connected(connected, desc)
        self.command_panel.append_console(f"[serial] {'connected' if connected else 'disconnected'} {desc}")

    def _on_line(self, line: str):
        self.command_panel.append_console(line)

    def _append_log_error(self, text: str):
        self.command_panel.append_console(f"[error] {text}")

    def _on_stats(self, stats: dict):
        self._last_rx_ms = int(stats.get("last_rx_ms", 0))
        self.status_panel.update_comm(
            rx_frames=int(stats.get("rx_frames", 0)),
            tx_frames=int(stats.get("tx_frames", 0)),
            parse_errors=int(stats.get("parse_errors", 0)),
            latency_ms=int(stats.get("last_latency_ms", 0)),
        )

    def _on_telemetry(self, t: Telemetry):
        self._latest_telemetry = t

        now_s = time.monotonic() - self._start_monotonic
        algo_name = ALGO_NAME.get(t.algo_id, f"ALG_{t.algo_id}")
        self.status_panel.update_control(algo_name, t.run_state, t.ref, t.feedback, t.u_cmd)
        self.plot_panel.append(
            now_s,
            {
                "ref": t.ref,
                "feedback": t.feedback,
                "u_cmd": t.u_cmd,
                "roll": t.roll,
                "pitch": t.pitch,
                "yaw": t.yaw,
            },
        )

        if self.recorder.active:
            row = telemetry_to_record_dict(t)
            row["pc_time_ms"] = int(time.time() * 1000)
            self.recorder.write_row(row)

    def _on_sim_tick(self):
        now = time.monotonic()
        dt = max(1e-4, now - self._last_sim_time)
        self._last_sim_time = now

        feedback = self.sim.step(dt, self._latest_telemetry.u_cmd)
        self._latest_feedback = feedback

        now_s = time.monotonic() - self._start_monotonic
        self.plot_panel.append(
            now_s,
            {
                "feedback": feedback.depth,
                "depth_rate": feedback.depth_rate,
                "disturbance": feedback.disturbance,
            },
        )

        tx_period = 1.0 / max(1, self.cfg.serial_tx_hz)
        if now - self._last_serial_tx >= tx_period:
            self.send_feedback_signal.emit(feedback)
            self._last_serial_tx = now

        if self.recorder.active:
            self.recorder.write_row(
                {
                    "pc_time_ms": int(time.time() * 1000),
                    "sim_depth": feedback.depth,
                    "sim_depth_rate": feedback.depth_rate,
                    "sim_disturbance": feedback.disturbance,
                }
            )

    def _update_timeout_state(self):
        if self._last_rx_ms <= 0:
            self.status_panel.set_timeout(False)
            return
        timeout = (int(time.time() * 1000) - self._last_rx_ms) > self.cfg.communication_timeout_ms
        self.status_panel.set_timeout(timeout)


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec_()

