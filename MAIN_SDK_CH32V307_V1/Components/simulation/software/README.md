# PyQt Control Simulation Host

This folder contains a modular PyQt-based host simulator for control algorithm HIL-lite testing.

## Features
- Serial connection over Bluetooth transparent UART.
- Command console for algorithm control (`ALG`, `SET`, `RUN`, `GET`, `SAVE`).
- Real-time VOFA+-style multi-channel waveform display.
- 1-DOF plant simulation (depth/height) running on the host.
- Data logging to CSV and replay-friendly event markers.

## Quick Start
1. Install Python 3.10+.
2. Install dependencies:
   - `pip install -r requirements_pyqt.txt`
3. Run:
   - `python run.py`

## Suggested Telemetry Format
The app accepts both:
- Binary frame: `AA 55 | msg_id | len | seq | payload | crc16`
- Text line: `key=value,key=value` or JSON line

Recommended telemetry keys:
- `timestamp, roll, pitch, yaw, u_cmd, ref, feedback, algo_id, run_state`

Recommended feedback keys sent to device:
- `timestamp, depth, depth_rate, disturbance`

