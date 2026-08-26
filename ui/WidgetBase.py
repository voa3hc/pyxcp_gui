from collections.abc import Mapping

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QMdiSubWindow

class WidgetBase(QMdiSubWindow):
    
    closed = pyqtSignal(object)   # emit self

    def __init__(self, data_manager, parent):
        super().__init__(parent)

        self.data_manager = data_manager
        self._value_items = {}
        self._owned_signals = set()
        
        #Allow closing
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._value_items = {}

    def closeEvent(self, event):
        for name in tuple(self._owned_signals):
            self.data_manager.release_signal(name, self)
        self._owned_signals.clear()
        self.closed.emit(self)   # notify parent
        super().closeEvent(event)

    def acquire_signal(self, name: str) -> None:
        self.data_manager.acquire_signal(name, self)
        self._owned_signals.add(name)

    def release_signal(self, name: str) -> None:
        self.data_manager.release_signal(name, self)
        self._owned_signals.discard(name)

    def export_state(self):
        """Return the common persisted state for every MDI widget."""
        return {
            "window_title": self.windowTitle(),
            "geometry": {
                "x": self.x(),
                "y": self.y(),
                "width": self.width(),
                "height": self.height(),
            },
            "visible": self.isVisible(),
            "maximized": self.isMaximized(),
            "minimized": self.isMinimized(),
        }

    def import_state(self, state):
        """Restore common state; subclasses may extend this method."""
        if not isinstance(state, Mapping):
            return

        title = state.get("window_title")
        if isinstance(title, str):
            self.setWindowTitle(title)

        geometry = state.get("geometry")
        if isinstance(geometry, Mapping):
            width = geometry.get("width")
            height = geometry.get("height")
            x = geometry.get("x")
            y = geometry.get("y")

            if isinstance(width, int) and isinstance(height, int):
                self.resize(max(1, width), max(1, height))
            if isinstance(x, int) and isinstance(y, int):
                self.move(x, y)

        if state.get("maximized") is True:
            self.showMaximized()
        elif state.get("minimized") is True:
            self.showMinimized()
        elif state.get("visible") is True:
            self.showNormal()


    def start(self):
        pass
        #self._refresh_timer.start()

    def stop(self):
        pass
    #self._refresh_timer.stop()

    def refresh_widgets(self):
        updates = self.data_manager.get_signal_data()
        for name, sv in updates.items():
            item = self._value_items.get(name)
            if item is not None:
                item.setText(f"{sv.value:.3f}")
