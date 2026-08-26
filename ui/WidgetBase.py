from collections.abc import Mapping
from PyQt6.QtWidgets import (
    QInputDialog,
    QMenu,
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QMdiSubWindow

class WidgetBase(QMdiSubWindow):
    
    closed = pyqtSignal(object)   # emit self

    def __init__(self, data_manager, parent):
        super().__init__(parent)
        # Inner widget (actual UI)
        self._centralWidget = QWidget()
        self.setWidget(self._centralWidget)
        
        self._mainWidgetLayout = QVBoxLayout(self._centralWidget)

        self._createTable()

        self._dataManager = data_manager
        self._valueItems = {}
        self._ownedSignals = set()
        
        #Allow closing
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._valueItems = {}

    def _createTable(self):
        
        self._tableWidget = QTableWidget(0, 3)
        self._tableWidget.setHorizontalHeaderLabels(["Name", "Value", "Unit"])
        self._tableWidget.verticalHeader().setVisible(False)
        self._tableWidget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tableWidget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tableWidget.setAlternatingRowColors(True)
        self._tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tableWidget.customContextMenuRequested.connect(self._show_context_menu)
        self._tableWidget.setColumnWidth(0, 260)
        self._tableWidget.setColumnWidth(1, 100)
        self._tableWidget.setColumnWidth(2, 70)
        self._mainWidgetLayout.addWidget(self._tableWidget)
    # --------------------------------------------------
    def _addRow(self, name, value, unit):
        name = str(name).strip()
        if not name:
            return

        row = self._tableWidget.rowCount()
        self._tableWidget.insertRow(row)

        name_item = QTableWidgetItem(name)
        value_item = QTableWidgetItem(str(value))
        unit_item = QTableWidgetItem(unit)

        name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self._tableWidget.setItem(row, 0, name_item)
        self._tableWidget.setItem(row, 1, value_item)
        self._tableWidget.setItem(row, 2, unit_item)

        self._valueItems[name] = value_item
        self.acquireSignal(name)

    ##########################################
    # contex menu
    def _show_context_menu(self, position):
        item = self._tableWidget.itemAt(position)
        if item is not None:
            self._tableWidget.selectRow(item.row())

        menu = QMenu(self._tableWidget)
        add_action = menu.addAction("Add item")
        remove_action = menu.addAction("Remove item")
        menu.addSeparator()

        width_menu = menu.addMenu("Auto set column width")
        auto_all_action = width_menu.addAction("All columns")
        column_actions = {
            self._tableWidget.horizontalHeaderItem(column).text(): width_menu.addAction(
                self._tableWidget.horizontalHeaderItem(column).text()
            )
            for column in range(self._tableWidget.columnCount())
            if self._tableWidget.horizontalHeaderItem(column) is not None
        }

        action = menu.exec(self._tableWidget.viewport().mapToGlobal(position))
        if action == add_action:
            self.addItem()
        elif action == remove_action:
            self.removeSelectedItem()
        elif action == auto_all_action:
            self.autoSetColumnWidth()
        elif action in column_actions.values():
            self.autoSetColumnWidth(action.text())

    def _signalNameColumn(self):
        """Column containing the signal name for the shared menu actions."""
        return 0

    def addItem(self):
        name, accepted = QInputDialog.getText(
            self,
            "Add measurement",
            "Signal name:",
        )
        if not accepted or not name.strip():
            return

        name = name.strip()
        if name in self._valueItems:
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
            self._addRow(name, value, unit)

    def removeSelectedItem(self):
        rows = sorted(
            {index.row() for index in self._tableWidget.selectionModel().selectedRows()},
            reverse=True,
        )
        for row in rows:
            name_item = self._tableWidget.item(row, self._signalNameColumn())
            name = name_item.text() if name_item is not None else ""
            self._tableWidget.removeRow(row)
            if name and not self._hasSignalRow(name):
                self._valueItems.pop(name, None)
                self.releaseSignal(name)

        self._rebuildValueItems()

    def _hasSignalRow(self, name):
        return any(
            self._tableWidget.item(row, self._signalNameColumn()) is not None
            and self._tableWidget.item(row, self._signalNameColumn()).text() == name
            for row in range(self._tableWidget.rowCount())
        )

    def _rebuildValueItems(self):
        self._valueItems = {
            self._tableWidget.item(row, self._signalNameColumn()).text(): self._tableWidget.item(row, self._signalValueColumn())
            for row in range(self._tableWidget.rowCount())
            if self._tableWidget.item(row, self._signalNameColumn()) is not None
            and self._tableWidget.item(row, self._signalValueColumn()) is not None
        }

    def _signalValueColumn(self):
        return 1

    def autoSetColumnWidth(self, column=None):
        columns = range(self._tableWidget.columnCount())
        if column is not None:
            columns = [self._tableWidget.horizontalHeaderItem(i).text() for i in columns]
            column = columns.index(column)
            columns = [column]

        for index in columns:
            self._tableWidget.resizeColumnToContents(index)
    ##########################################
    # State
    def closeEvent(self, event):
        for name in tuple(self._ownedSignals):
            self._dataManager.releaseSignal(name, self)
        self._ownedSignals.clear()
        self.closed.emit(self)   # notify parent
        super().closeEvent(event)

    def acquireSignal(self, name: str) -> None:
        self._dataManager.acquireSignal(name, self)
        self._ownedSignals.add(name)

    def releaseSignal(self, name: str) -> None:
        self._dataManager.releaseSignal(name, self)
        self._ownedSignals.discard(name)

    def exportState(self):
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

    def importState(self, state):
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


    def startAcquisition(self):
        pass
        #self._refresh_timer.start()

    def stopAcquisition(self):
        pass
    
    def resetAcquisition(self):
        pass

    def refreshData(self):
        updates = self._dataManager.getSignalData()
        for name, sv in updates.items():
            item = self._valueItems.get(name)
            if item is not None:
                item.setText(f"{sv.value:.3f}")
