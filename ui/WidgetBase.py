from collections.abc import Mapping

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QInputDialog,
    QMenu,
    QMdiSubWindow,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class WidgetBase(QMdiSubWindow):
    closed = pyqtSignal(object)

    def __init__(self, data_manager, parent):
        super().__init__(parent)
        self._central_widget = QWidget()
        self.setWidget(self._central_widget)
        self._main_layout = QVBoxLayout(self._central_widget)
        self._create_table()
        self._data_manager = data_manager
        self._value_items = {}
        self._owned_signals = set()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    def _create_table(self):
        self._table_widget = QTableWidget(0, 3)
        self._table_widget.setHorizontalHeaderLabels(["Name", "Value", "Unit"])
        self._table_widget.verticalHeader().setVisible(False)
        self._table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_widget.setAlternatingRowColors(True)
        self._table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table_widget.customContextMenuRequested.connect(self._show_context_menu)
        self._table_widget.setColumnWidth(0, 260)
        self._table_widget.setColumnWidth(1, 100)
        self._table_widget.setColumnWidth(2, 70)
        self._main_layout.addWidget(self._table_widget)

    def _add_row(self, name, value, unit):
        name = str(name).strip()
        if not name:
            return

        row = self._table_widget.rowCount()
        self._table_widget.insertRow(row)
        name_item = QTableWidgetItem(name)
        value_item = QTableWidgetItem(str(value))
        unit_item = QTableWidgetItem(unit)
        name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table_widget.setItem(row, 0, name_item)
        self._table_widget.setItem(row, 1, value_item)
        self._table_widget.setItem(row, 2, unit_item)
        self._value_items[name] = value_item
        self.acquire_signal(name)

    def _show_context_menu(self, position):
        item = self._table_widget.itemAt(position)
        if item is not None:
            self._table_widget.selectRow(item.row())

        menu = QMenu(self._table_widget)
        add_action = menu.addAction("Add item")
        remove_action = menu.addAction("Remove item")
        menu.addSeparator()
        width_menu = menu.addMenu("Auto set column width")
        auto_all_action = width_menu.addAction("All columns")
        column_actions = {
            self._table_widget.horizontalHeaderItem(column).text(): width_menu.addAction(
                self._table_widget.horizontalHeaderItem(column).text()
            )
            for column in range(self._table_widget.columnCount())
            if self._table_widget.horizontalHeaderItem(column) is not None
        }

        action = menu.exec(self._table_widget.viewport().mapToGlobal(position))
        if action == add_action:
            self.add_item()
        elif action == remove_action:
            self.remove_selected_item()
        elif action == auto_all_action:
            self.auto_set_column_width()
        elif action in column_actions.values():
            self.auto_set_column_width(action.text())

    def _signal_name_column(self):
        return 0

    def _signal_value_column(self):
        return 1

    def add_item(self):
        name, accepted = QInputDialog.getText(self, "Add measurement", "Signal name:")
        if not accepted or not name.strip():
            return
        name = name.strip()
        if name in self._value_items:
            return
        value, accepted = QInputDialog.getText(
            self, "Add measurement", "Initial value:", text="0"
        )
        if not accepted:
            return
        unit, accepted = QInputDialog.getText(
            self, "Add measurement", "Unit:", text="[-]"
        )
        if accepted:
            self._add_row(name, value, unit)

    def remove_selected_item(self):
        rows = sorted(
            {index.row() for index in self._table_widget.selectionModel().selectedRows()},
            reverse=True,
        )
        for row in rows:
            name_item = self._table_widget.item(row, self._signal_name_column())
            name = name_item.text() if name_item is not None else ""
            self._table_widget.removeRow(row)
            if name and not self._has_signal_row(name):
                self._value_items.pop(name, None)
                self.release_signal(name)
        self._rebuild_value_items()

    def _has_signal_row(self, name):
        return any(
            self._table_widget.item(row, self._signal_name_column()) is not None
            and self._table_widget.item(row, self._signal_name_column()).text() == name
            for row in range(self._table_widget.rowCount())
        )

    def _rebuild_value_items(self):
        self._value_items = {
            self._table_widget.item(row, self._signal_name_column()).text(): self._table_widget.item(
                row, self._signal_value_column()
            )
            for row in range(self._table_widget.rowCount())
            if self._table_widget.item(row, self._signal_name_column()) is not None
            and self._table_widget.item(row, self._signal_value_column()) is not None
        }

    def auto_set_column_width(self, column=None):
        columns = range(self._table_widget.columnCount())
        if column is not None:
            headers = [self._table_widget.horizontalHeaderItem(i).text() for i in columns]
            columns = [headers.index(column)]
        for index in columns:
            self._table_widget.resizeColumnToContents(index)

    def closeEvent(self, event):
        for name in tuple(self._owned_signals):
            self._data_manager.release_signal(name, self)
        self._owned_signals.clear()
        self.closed.emit(self)
        super().closeEvent(event)

    def acquire_signal(self, name: str) -> None:
        self._data_manager.acquire_signal(name, self)
        self._owned_signals.add(name)

    def release_signal(self, name: str) -> None:
        self._data_manager.release_signal(name, self)
        self._owned_signals.discard(name)

    def export_state(self):
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

    def start_acquisition(self):
        pass

    def stop_acquisition(self):
        pass

    def reset_acquisition(self):
        pass

    def refresh_data(self):
        updates = self._data_manager.get_signal_data()
        for name, scalar_value in updates.items():
            item = self._value_items.get(name)
            if item is not None:
                item.setText(f"{scalar_value.value:.3f}")
