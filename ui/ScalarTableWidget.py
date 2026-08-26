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

from ui.MeasureTableWidget import MeasureTableWidget

class ScalarTableWidget(MeasureTableWidget):
    
    def __init__(self, data_manager, parent=None):
        super().__init__(data_manager, parent)
        # optional
        self.setWindowTitle("Scalar Table")
        # populate
        self._populateExampleData()

    # --------------------------------------------------
    def _populateExampleData(self):
        signals = [
            ("InjHyd_swtRefEveEOE_C", "0.00", "[-]"),
            ("InjHyd_swtEnaRef_C", "9.00", "[-]"),
            ("HLSDem_flgSwtSelSwShrSpl_C", "1.0", "[-]"),
            ("HLSdem_nSetPloDia_C", "0.000", "[rpm]"),
            ("DSMAUX_xClearTrg_C", "00h", "[hex]"),
        ]

        for name, value, unit in signals:
            self._addRow(name, value, unit)

    