import binascii
import json
import struct
import time
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

from .models import SimFeedback, Telemetry


FRAME_HEAD = b"\xAA\x55"
MSG_TELEMETRY = 0x01
MSG_SIM_FEEDBACK = 0x10
MSG_ACK = 0x20


def crc16_ccitt(data: bytes) -> int:
    return binascii.crc_hqx(data, 0xFFFF)


def _safe_float(v: object, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v: object, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _decode_text_line(line: str) -> Optional[Dict[str, object]]:
    line = line.strip()
    if not line:
        return None

    if line.startswith("{") and line.endswith("}"):
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            return None
        return None

    if "=" in line:
        out: Dict[str, object] = {}
        for item in line.split(","):
            if "=" not in item:
                continue
            k, v = item.split("=", 1)
            out[k.strip()] = v.strip()
        return out if out else None

    if line.upper().startswith("OK") or line.upper().startswith("ERR"):
        return {"ack": line}

    return {"line": line}


def dict_to_telemetry(raw: Dict[str, object]) -> Telemetry:
    mapped = {k.lower(): v for k, v in raw.items()}
    telemetry = Telemetry(
        timestamp_ms=_safe_int(mapped.get("timestamp", mapped.get("timestamp_ms", 0))),
        roll=_safe_float(mapped.get("roll", 0.0)),
        pitch=_safe_float(mapped.get("pitch", 0.0)),
        yaw=_safe_float(mapped.get("yaw", 0.0)),
        u_cmd=_safe_float(mapped.get("u_cmd", mapped.get("u", 0.0))),
        ref=_safe_float(mapped.get("ref", 0.0)),
        feedback=_safe_float(mapped.get("feedback", mapped.get("depth", 0.0))),
        algo_id=_safe_int(mapped.get("algo_id", 0)),
        run_state=_safe_int(mapped.get("run_state", 0)),
    )
    known = {
        "timestamp",
        "timestamp_ms",
        "roll",
        "pitch",
        "yaw",
        "u_cmd",
        "u",
        "ref",
        "feedback",
        "depth",
        "algo_id",
        "run_state",
    }
    for k, v in mapped.items():
        if k in known:
            continue
        telemetry.extra[k] = _safe_float(v, 0.0)

    if telemetry.timestamp_ms <= 0:
        telemetry.timestamp_ms = int(time.time() * 1000)
    return telemetry


def encode_feedback_binary(seq: int, feedback: SimFeedback) -> bytes:
    payload = struct.pack(
        "<Ifff",
        int(feedback.timestamp_ms),
        float(feedback.depth),
        float(feedback.depth_rate),
        float(feedback.disturbance),
    )
    header = FRAME_HEAD + bytes([MSG_SIM_FEEDBACK, len(payload)]) + struct.pack("<H", seq & 0xFFFF)
    crc = crc16_ccitt(header + payload)
    return header + payload + struct.pack("<H", crc)


def encode_feedback_text(feedback: SimFeedback) -> bytes:
    text = (
        f"timestamp={feedback.timestamp_ms},depth={feedback.depth:.5f},"
        f"depth_rate={feedback.depth_rate:.5f},disturbance={feedback.disturbance:.5f}\n"
    )
    return text.encode("ascii", errors="ignore")


class StreamParser:
    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, chunk: bytes) -> Tuple[List[Telemetry], List[str], int]:
        self._buf.extend(chunk)
        telemetry_list: List[Telemetry] = []
        lines: List[str] = []
        parse_errors = 0

        while True:
            if not self._buf:
                break

            if self._buf.startswith(FRAME_HEAD):
                msg = self._try_parse_binary()
                if msg is None:
                    break
                if msg == "ERR":
                    parse_errors += 1
                    continue
                kind, payload = msg
                if kind == MSG_TELEMETRY:
                    telemetry_list.append(payload)
                elif kind == MSG_ACK:
                    lines.append(str(payload))
                continue

            newline_idx = self._buf.find(b"\n")
            if newline_idx < 0:
                if len(self._buf) > 4096:
                    self._buf.clear()
                    parse_errors += 1
                break

            raw = self._buf[: newline_idx + 1]
            del self._buf[: newline_idx + 1]
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            parsed = _decode_text_line(line)
            if parsed is None:
                parse_errors += 1
                continue
            if "ack" in parsed:
                lines.append(str(parsed["ack"]))
            elif "line" in parsed:
                lines.append(str(parsed["line"]))
            else:
                telemetry_list.append(dict_to_telemetry(parsed))

        return telemetry_list, lines, parse_errors

    def _try_parse_binary(self):
        if len(self._buf) < 8:
            return None
        if not self._buf.startswith(FRAME_HEAD):
            return "ERR"

        msg_id = self._buf[2]
        payload_len = self._buf[3]
        frame_len = 2 + 1 + 1 + 2 + payload_len + 2
        if len(self._buf) < frame_len:
            return None

        frame = bytes(self._buf[:frame_len])
        del self._buf[:frame_len]

        got_crc = struct.unpack("<H", frame[-2:])[0]
        calc_crc = crc16_ccitt(frame[:-2])
        if got_crc != calc_crc:
            return "ERR"

        payload = frame[6:-2]
        if msg_id == MSG_TELEMETRY:
            if payload_len < struct.calcsize("<IfffffBB"):
                return "ERR"
            ts, roll, pitch, yaw, u_cmd, ref, algo_id, run_state = struct.unpack("<IfffffBB", payload[:26])
            tele = Telemetry(
                timestamp_ms=int(ts),
                roll=float(roll),
                pitch=float(pitch),
                yaw=float(yaw),
                u_cmd=float(u_cmd),
                ref=float(ref),
                algo_id=int(algo_id),
                run_state=int(run_state),
            )
            return MSG_TELEMETRY, tele
        if msg_id == MSG_ACK:
            text = payload.decode("utf-8", errors="ignore")
            return MSG_ACK, text
        return "ERR"


def telemetry_to_record_dict(t: Telemetry) -> Dict[str, object]:
    out = asdict(t)
    extra = out.pop("extra", {})
    out.update(extra)
    return out

