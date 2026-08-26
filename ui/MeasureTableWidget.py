
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
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
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
        name = str(name).strip()
        if not name:
            return

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
        self.acquire_signal(name)

    def _show_context_menu(self, position):
        item = self.table.itemAt(position)
        if item is not None:
            self.table.selectRow(item.row())

        menu = QMenu(self.table)
        add_action = menu.addAction("Add item")
        remove_action = menu.addAction("Remove item")
        menu.addSeparator()

        width_menu = menu.addMenu("Auto set column width")
        auto_all_action = width_menu.addAction("All columns")
        auto_name_action = width_menu.addAction("Name")
        auto_value_action = width_menu.addAction("Value")
        auto_unit_action = width_menu.addAction("Unit")

        action = menu.exec(self.table.viewport().mapToGlobal(position))
        if action == add_action:
            self.add_item()
        elif action == remove_action:
            self.remove_selected_item()
        elif action == auto_all_action:
            self.auto_set_column_width()
        elif action in (auto_name_action, auto_value_action, auto_unit_action):
            self.auto_set_column_width(action.text())

    def add_item(self):
        name, accepted = QInputDialog.getText(
            self,
            "Add measurement",
            "Signal name:",
        )
        if not accepted or not name.strip():
            return

        name = name.strip()
        if name in self._value_items:
            return

        value, accepted = QInputDialog.getText(
            self,
            "Add measurement",
            "Initial value:",
            text="0",
        )
        if not accepted:
            return

        unit, accepted = QInputDialog.getText(
            self,
            "Add measurement",
            "Unit:",
            text="[-]",
        )
        if accepted:
            self._add_row(name, value, unit)

    def remove_selected_item(self):
        rows = sorted(
            {index.row() for index in self.table.selectionModel().selectedRows()},
            reverse=True,
        )
        for row in rows:
            name_item = self.table.item(row, 0)
            name = name_item.text() if name_item is not None else ""
            self.table.removeRow(row)
            if name and not self._has_signal_row(name):
                self._value_items.pop(name, None)
                self.release_signal(name)

        self._rebuild_value_items()

    def _has_signal_row(self, name):
        return any(
            self.table.item(row, 0) is not None
            and self.table.item(row, 0).text() == name
            for row in range(self.table.rowCount())
        )

    def _rebuild_value_items(self):
        self._value_items = {
            self.table.item(row, 0).text(): self.table.item(row, 1)
            for row in range(self.table.rowCount())
            if self.table.item(row, 0) is not None
            and self.table.item(row, 1) is not None
        }

    def auto_set_column_width(self, column=None):
        columns = range(self.table.columnCount())
        if column is not None:
            columns = [self.table.horizontalHeaderItem(i).text() for i in columns]
            column = columns.index(column)
            columns = [column]

        for index in columns:
            self.table.resizeColumnToContents(index)

    # --------------------------------------------------
    def export_state(self):
        data = []
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text()
            value = self.table.item(row, 1).text()
            unit = self.table.item(row, 2).text()
            data.append((name, value, unit))

        column_widths = [
            self.table.columnWidth(col)
            for col in range(self.table.columnCount())
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
        self.table.setRowCount(0)
        self._value_items.clear()
        for name, value, unit in state.get("data", []):
            self._add_row(name, value, unit)

        # restore column widths
        widths = state.get("column_widths", [])
        for col, w in enumerate(widths):
            if col < self.table.columnCount():
                self.table.setColumnWidth(col, w)
