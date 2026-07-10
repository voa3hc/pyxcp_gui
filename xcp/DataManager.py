# DataManager.py
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Dict, List, Tuple, Set

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

    # -----------------------------
    # Signal registration
    # -----------------------------
    def add_signal(self, name: str) -> None:
        with self._lock:
            if name in self._signals.keys():
                return
            self._signals[name] = ScalarValue(0, 0)

    def remove_signal(self, name: str) -> None:
        with self._lock:
            if name not in self._signals.keys():
                return
            self._signals.remove(name)

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
