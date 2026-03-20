import time
from typing import Optional

from PyQt5 import QtCore

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover
    serial = None
    list_ports = None

from .models import SimFeedback
from .protocol import StreamParser, encode_feedback_binary, encode_feedback_text


class SerialWorker(QtCore.QObject):
    telemetry_received = QtCore.pyqtSignal(object)
    line_received = QtCore.pyqtSignal(str)
    comm_stats = QtCore.pyqtSignal(dict)
    connection_changed = QtCore.pyqtSignal(bool, str)
    error = QtCore.pyqtSignal(str)

    def __init__(self, use_binary_tx: bool = True) -> None:
        super().__init__()
        self._serial: Optional["serial.Serial"] = None
        self._port_name = ""
        self._baudrate = 115200
        self._running = False
        self._seq = 0
        self._parser = StreamParser()
        self._use_binary_tx = use_binary_tx
        self._rx_frames = 0
        self._tx_frames = 0
        self._parse_errors = 0
        self._dropped = 0
        self._last_rx_ms = 0
        self._last_latency_ms = 0

        self._read_timer = QtCore.QTimer(self)
        self._read_timer.setInterval(10)
        self._read_timer.timeout.connect(self._poll_read)

        self._stats_timer = QtCore.QTimer(self)
        self._stats_timer.setInterval(500)
        self._stats_timer.timeout.connect(self._emit_stats)

    @QtCore.pyqtSlot(str, int)
    def open(self, port_name: str, baudrate: int) -> None:
        if serial is None:
            self.error.emit("pyserial not installed")
            return
        self.close()
        try:
            self._serial = serial.Serial(port=port_name, baudrate=baudrate, timeout=0.0)
            self._port_name = port_name
            self._baudrate = baudrate
            self._running = True
            self._read_timer.start()
            self._stats_timer.start()
            self.connection_changed.emit(True, f"{port_name}@{baudrate}")
        except Exception as exc:
            self._serial = None
            self._running = False
            self.error.emit(f"Open serial failed: {exc}")
            self.connection_changed.emit(False, "")

    @QtCore.pyqtSlot()
    def close(self) -> None:
        self._running = False
        self._read_timer.stop()
        self._stats_timer.stop()
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        self.connection_changed.emit(False, "")

    @QtCore.pyqtSlot(str)
    def send_line(self, text: str) -> None:
        if not self._serial:
            return
        payload = (text.rstrip("\r\n") + "\n").encode("utf-8", errors="ignore")
        try:
            self._serial.write(payload)
            self._tx_frames += 1
        except Exception as exc:
            self.error.emit(f"Serial send failed: {exc}")

    @QtCore.pyqtSlot(object)
    def send_feedback(self, feedback: SimFeedback) -> None:
        if not self._serial:
            return
        try:
            if self._use_binary_tx:
                payload = encode_feedback_binary(self._seq, feedback)
            else:
                payload = encode_feedback_text(feedback)
            self._serial.write(payload)
            self._tx_frames += 1
            self._seq = (self._seq + 1) & 0xFFFF
        except Exception as exc:
            self.error.emit(f"Serial send feedback failed: {exc}")

    @QtCore.pyqtSlot(bool)
    def set_binary_tx(self, enabled: bool) -> None:
        self._use_binary_tx = bool(enabled)

    def _poll_read(self) -> None:
        if not self._running or not self._serial:
            return
        try:
            chunk = self._serial.read(1024)
            if not chunk:
                return
            now_ms = int(time.time() * 1000)
            telemetry_list, lines, parse_errors = self._parser.feed(chunk)
            self._parse_errors += parse_errors
            for telemetry in telemetry_list:
                self._rx_frames += 1
                self._last_rx_ms = now_ms
                if telemetry.timestamp_ms > 0:
                    self._last_latency_ms = max(0, now_ms - telemetry.timestamp_ms)
                self.telemetry_received.emit(telemetry)
            for line in lines:
                self.line_received.emit(line)
        except Exception as exc:
            self.error.emit(f"Serial read failed: {exc}")
            self.close()

    def _emit_stats(self) -> None:
        self.comm_stats.emit(
            {
                "rx_frames": self._rx_frames,
                "tx_frames": self._tx_frames,
                "parse_errors": self._parse_errors,
                "dropped": self._dropped,
                "last_rx_ms": self._last_rx_ms,
                "last_latency_ms": self._last_latency_ms,
            }
        )

    @staticmethod
    def list_ports():
        if list_ports is None:
            return []
        return [p.device for p in list_ports.comports()]
