
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,QTableWidgetItem, QAbstractItemView,
    QTableWidgetItem
)
from ui.WidgetBase import WidgetBase

class MeasureTableWidget(WidgetBase):
    
    def __init__(self, data_manager, parent=None):
        super().__init__(data_manager, parent)

        # Inner widget (actual UI)
        self._central = QWidget()
        self.setWidget(self._central)

        layout = QVBoxLayout(self._central)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Value", "Unit"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 260)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 70)
        #Set default size
        #self.resize(400, 300)

        layout.addWidget(self.table)

        # Optional: set window title
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
    def _add_row(self, name, value, unit):
        row = self.table.rowCount()
        self.table.insertRow(row)

        name_item = QTableWidgetItem(name)
        value_item = QTableWidgetItem(str(value))
        unit_item = QTableWidgetItem(unit)

        name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, value_item)
        self.table.setItem(row, 2, unit_item)

        self._value_items[name] = value_item
        self.data_manager.add_signal(name)

    # --------------------------------------------------
    def export_state(self):
        data = []
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text()
            value = self.table.item(row, 1).text()
            unit = self.table.item(row, 2).text()
            data.append((name, value, unit))

            # save column widths
            column_widths = []
            for col in range(self.table.columnCount()):
                column_widths.append(self.table.columnWidth(col))

        return {
                "data": data,
                "geometry": {  # add geometry
                    "x": self.x(),
                    "y": self.y(),
                    "width": self.width(),
                    "height": self.height()
                },
                "column_widths": column_widths
            }


    def import_state(self, state):
        self.table.setRowCount(0)
        for name, value, unit in state.get("data", []):
            self._add_row(name, value, unit)

        # restore geometry
        geo = state.get("geometry", None)
        if geo:
            self.resize(geo.get("width", 400), geo.get("height", 300))
            self.move(geo.get("x", 100), geo.get("y", 100))


        # restore column widths
        widths = state.get("column_widths", [])
        for col, w in enumerate(widths):
            if col < self.table.columnCount():
                self.table.setColumnWidth(col, w)
