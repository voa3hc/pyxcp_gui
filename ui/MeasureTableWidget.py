
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QInputDialog,
    QMenu,
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
)
from ui.WidgetBase import WidgetBase

class MeasureTableWidget(WidgetBase):
    
    def __init__(self, data_manager, parent=None):
        super().__init__(data_manager, parent)

        # Set window title
        self.setWindowTitle("Measurement Table")

        self._populate_example_signals()


    # --------------------------------------------------
    def _populate_example_signals(self):
        signals = [
            ("TestVar1_u8", 0, "[-]"),
            ("TestVar2_u8", 0, "[-]")
        ]

        for name, value, unit in signals:
            self._add_row(name, value, unit)

    # --------------------------------------------------
    def export_state(self):
        data = []
        for row in range(self._table_widget.rowCount()):
            name = self._table_widget.item(row, 0).text()
            value = self._table_widget.item(row, 1).text()
            unit = self._table_widget.item(row, 2).text()
            data.append((name, value, unit))

        column_widths = [
            self._table_widget.columnWidth(col)
            for col in range(self._table_widget.columnCount())
        ]

        state = super().export_state()
        state.update({
            "data": data,
            "column_widths": column_widths,
        })
        return state


    def import_state(self, state):
        if not isinstance(state, dict):
            return

        super().import_state(state)
        for name in tuple(self._owned_signals):
            self.release_signal(name)
        self._table_widget.setRowCount(0)
        self._value_items.clear()
        for name, value, unit in state.get("data", []):
            self._add_row(name, value, unit)

        # restore column widths
        widths = state.get("column_widths", [])
        for col, w in enumerate(widths):
            if col < self._table_widget.columnCount():
                self._table_widget.setColumnWidth(col, w)
