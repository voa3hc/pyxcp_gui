
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
            self._addRow(name, value, unit)

    # --------------------------------------------------
    def exportState(self):
        data = []
        for row in range(self._tableWidget.rowCount()):
            name = self._tableWidget.item(row, 0).text()
            value = self._tableWidget.item(row, 1).text()
            unit = self._tableWidget.item(row, 2).text()
            data.append((name, value, unit))

        column_widths = [
            self._tableWidget.columnWidth(col)
            for col in range(self._tableWidget.columnCount())
        ]

        state = super().exportState()
        state.update({
            "data": data,
            "column_widths": column_widths,
        })
        return state


    def importState(self, state):
        if not isinstance(state, dict):
            return

        super().importState(state)
        for name in tuple(self._ownedSignals):
            self.releaseSignal(name)
        self._tableWidget.setRowCount(0)
        self._valueItems.clear()
        for name, value, unit in state.get("data", []):
            self._addRow(name, value, unit)

        # restore column widths
        widths = state.get("column_widths", [])
        for col, w in enumerate(widths):
            if col < self._tableWidget.columnCount():
                self._tableWidget.setColumnWidth(col, w)
