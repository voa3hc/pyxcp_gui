from PyQt6.QtCore import QTimer, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QMdiSubWindow,
)

class WidgetBase(QMdiSubWindow):
    
    closed = pyqtSignal(object)   # emit self

    def __init__(self, data_manager, parent):
        super().__init__(parent)

        self.data_manager = data_manager
        self._value_items = {}
        
        #Allow closing
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._value_items = {}

    def closeEvent(self, event):
        self.closed.emit(self)   # notify parent
        super().closeEvent(event)


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