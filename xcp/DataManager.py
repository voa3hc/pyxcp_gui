# DataManager.py
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Dict, Set, Tuple

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

@dataclass
class ScalarValue:
    timestamp: float
    value: float

class DataManager(QObject):
    """
    Central state for XCP data.
    Worker writes into this manager.
    Widgets pull snapshots on their own timers.
    """

    # low-frequency notification only: "something changed"
    data_arrived = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._lock = Lock()
        # all signal dict, name : time - value
        self._signals: Dict[str, ScalarValue] = {}
        self._signal_references: Dict[str, Set[int]] = {}

    # -----------------------------
    # Signal registration
    # -----------------------------
    def add_signal(self, name: str) -> None:
        with self._lock:
            self._ensure_signal(name)

    def acquire_signal(self, name: str, owner) -> None:
        """Register a signal and retain one reference for ``owner``."""
        with self._lock:
            self._ensure_signal(name)
            self._signal_references.setdefault(name, set()).add(id(owner))

    def release_signal(self, name: str, owner) -> None:
        """Release one owner's reference and remove unreferenced signals."""
        with self._lock:
            owners = self._signal_references.get(name)
            if owners is None:
                return

            owners.discard(id(owner))
            if owners:
                return

            self._signal_references.pop(name, None)
            self._signals.pop(name, None)

    def _ensure_signal(self, name: str) -> None:
        if name not in self._signals:
            self._signals[name] = ScalarValue(0, 0)

    def remove_signal(self, name: str) -> None:
        with self._lock:
            if self._signal_references.get(name):
                return
            self._signal_references.pop(name, None)
            self._signals.pop(name, None)

    # -----------------------------
    # Worker ingestion
    # Called by XcpWorker: timestamp  - name - value
    def ingest_signal(self, signal: Tuple[float, str, float]) -> None:
        changed = False
        with self._lock:
            time, name, value = signal
            self._signals[name].timestamp = time
            self._signals[name].value = value
            changed = True

        if changed:
            self.data_arrived.emit()

    # -----------------------------
    # Widget pull APIs
    # -----------------------------
    def get_signal_data(self) -> Dict[str, ScalarValue]:
        with self._lock:
            return self._signals
