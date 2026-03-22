import csv
from pathlib import Path
from typing import Dict, Optional


class CsvRecorder:
    def __init__(self) -> None:
        self._file = None
        self._writer = None
        self._fieldnames = None
        self._rows = []
        self.path: Optional[Path] = None

    @property
    def active(self) -> bool:
        return self._file is not None

    def start(self, path: Path) -> None:
        self.stop()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("w", newline="", encoding="utf-8")
        self.path = path
        self._writer = None
        self._fieldnames = None
        self._rows = []

    def _rewrite_file(self) -> None:
        if self._file is None or self._fieldnames is None:
            return
        self._file.seek(0)
        self._file.truncate(0)
        self._writer = csv.DictWriter(self._file, fieldnames=self._fieldnames)
        self._writer.writeheader()
        for row in self._rows:
            out = {k: row.get(k, "") for k in self._fieldnames}
            self._writer.writerow(out)
        self._file.flush()

    def write_row(self, row: Dict[str, object]) -> None:
        if self._file is None:
            return
        normalized = dict(row)
        if self._writer is None:
            self._fieldnames = list(normalized.keys())
            self._writer = csv.DictWriter(self._file, fieldnames=self._fieldnames)
            self._writer.writeheader()
        if self._fieldnames is None:
            return
        new_fields = [k for k in normalized.keys() if k not in self._fieldnames]
        self._rows.append(normalized)
        if new_fields:
            self._fieldnames.extend(new_fields)
            self._rewrite_file()
            return
        out = {k: normalized.get(k, "") for k in self._fieldnames}
        self._writer.writerow(out)
        self._file.flush()

    def stop(self) -> None:
        if self._file is not None:
            self._file.close()
        self._file = None
        self._writer = None
        self._fieldnames = None
        self._rows = []

