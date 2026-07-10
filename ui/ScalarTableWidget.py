import sys
import time
import math
import random
import collections

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QMdiArea,
    QMdiSubWindow,
    QWidgetAction,
    QTableWidget,QTableWidgetItem, QAbstractItemView,
    QTableWidgetItem, QHeaderView, QToolBar, QLabel, QHBoxLayout
)
from PyQt6.QtGui import QColor, QBrush
import pyqtgraph as pg

from ui.WidgetBase import WidgetBase

class ScalarTableWidget(WidgetBase):
    
    def __init__(self, data_manager, parent=None):
        super().__init__(data_manager, parent)
        # ✅ central widget đúng chuẩn
        self._central = QWidget()
        self.setWidget(self._central)

        layout = QVBoxLayout(self._central)

        # ✅ table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Value", "Unit"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.table.setAlternatingRowColors(True)

        self.table.setColumnWidth(0, 280)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 70)

        layout.addWidget(self.table)

        # optional
        self.setWindowTitle("Scalar Table")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # populate
        self._populate_example_data()

    # --------------------------------------------------
    def _populate_example_data(self):
        signals = [
            ("InjHyd_swtRefEveEOE_C", "0.00", "[-]"),
            ("InjHyd_swtEnaRef_C", "9.00", "[-]"),
            ("HLSDem_flgSwtSelSwShrSpl_C", "1.0", "[-]"),
            ("HLSdem_nSetPloDia_C", "0.000", "[rpm]"),
            ("DSMAUX_xClearTrg_C", "00h", "[hex]"),
        ]

        for name, value, unit in signals:
            self._add_row(name, value, unit)

    # --------------------------------------------------
    def _add_row(self, name, value, unit):
        row = self.table.rowCount()
        self.table.insertRow(row)

        name_item = QTableWidgetItem(name)
        name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

        value_item = QTableWidgetItem(value)
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        unit_item = QTableWidgetItem(unit)
        unit_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, value_item)
        self.table.setItem(row, 2, unit_item)
    
    def update_value(self, name: str, t: float, value: float):
        pass