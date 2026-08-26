import sys
import time
import math
import random
import collections
import pickle

from PyQt6.QtCore import QTimer, pyqtSignal, Qt
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

from ui import OscilloscopeWidgetV2
from ui import ScalarTableWidget
from ui import MeasureTableWidget
from xcp import XcpWorker

from xcp import DataManager

import json
from pathlib import Path


# ==========================================================
# MAIN APPLICATION WINDOW (MDI)
# ==========================================================
class MainWindow(QMainWindow):
    
    RECENT_PROJECT_FILE = Path("recent.exp")

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ECU Instrumentation Suite")
        self.resize(1100, 600)

        # --- MDI AREA ---
        self.mdiArea = QMdiArea()
        self.setCentralWidget(self.mdiArea)

        # --- XCP WORKER AND DATA MANAGER ---
        self.data_manager = DataManager.DataManager()
        self.worker = XcpWorker.XcpWorker()
        self.worker.signal_ready.connect(self.data_manager.ingest_signal)

        # --- MENUS ---
        self._create_menus()

        # Open first scope automatically
        self.mOslScopeWidgets = []
        self.mMeasureTableWidgets = []
        self.mScalarTableWidgets = []
 
        self.load_project()
        
        # Set up timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_all_widgets)
        self.refresh_timer.start(100)  # refresh every 100 ms


    # --------------------------------------------------
    # MENUS
    # --------------------------------------------------
    def _create_menus(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("File")

        new_scope_action = QWidgetAction(self)
        new_scope_action.setText("New Scope")
        new_scope_action.triggered.connect(self.new_scope)

        
        table_action = QWidgetAction(self)
        table_action.setText("New Scalar Table")
        table_action.triggered.connect(self.new_scalar_table)
    
        #file_menu.addSeparator()
        #file_menu.addAction(table_action)

        
        measure_action = QWidgetAction(self)
        measure_action.setText("New Measure Table")
        measure_action.triggered.connect(self.new_measure_table)


        close_action = QWidgetAction(self)
        close_action.setText("Close")
        close_action.triggered.connect(self.close_active_window)

        exit_action = QWidgetAction(self)
        exit_action.setText("Exit")
        exit_action.triggered.connect(self.close)

        file_menu.addActions([
            new_scope_action, table_action, measure_action,
            close_action
        ])
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        # Options Menu
        options_menu = menu_bar.addMenu("Options")

        start_action = QWidgetAction(self)
        start_action.setText("Start")
        start_action.triggered.connect(self.start_acquisition)

        stop_action = QWidgetAction(self)
        stop_action.setText("Stop")
        stop_action.triggered.connect(self.stop_acquisition)

        options_menu.addActions([
            start_action,
            stop_action
        ])

    def save_layout(self):
        return {
            "geometry": self.saveGeometry().data(),
            "state": self.saveState().data()
        }

    def load_layout(self, data):
        if data is not None:
            self.restoreGeometry(data["geometry"])
            self.restoreState(data["state"])

    def save_project(self, filename=RECENT_PROJECT_FILE):
        print("Saving project..")
        data = {
            "layout": self.save_layout(),
            "widgets": [],
        }

        widget_types = {
            OscilloscopeWidgetV2.OscilloscopeWidgetV2: "oscilloscope",
            MeasureTableWidget.MeasureTableWidget: "measure_table",
            ScalarTableWidget.ScalarTableWidget: "scalar_table",
        }

        for widget in self.mdiArea.subWindowList():
            widget_type = next(
                (name for cls, name in widget_types.items()
                 if isinstance(widget, cls)),
                None,
            )
            if widget_type is None:
                continue

            data["widgets"].append({
                "type": widget_type,
                "state": widget.export_state(),
            })

        # Keep the old field for consumers that still understand the legacy
        # measurement-table-only project format.
        data["measure_tables"] = [
            record for record in data["widgets"]
            if record["type"] == "measure_table"
        ]

        # save to bin file
        with open(filename, "wb") as f:
            pickle.dump(data, f)
    
    def load_project(self, filename=RECENT_PROJECT_FILE):
        print(f"load project {filename}")
        try:
            with open(filename, "rb") as f:
                data = pickle.load(f)

                # Loading replaces the current workspace instead of appending
                # another copy of every persisted subwindow.
                for widget in list(self.mdiArea.subWindowList()):
                    widget.close()
                self.mOslScopeWidgets.clear()
                self.mMeasureTableWidgets.clear()
                self.mScalarTableWidgets.clear()

                self.load_layout(data.get("layout", None))

                records = data.get("widgets")
                if records is None:
                    records = []
                    for legacy in data.get("measure_tables", []):
                        state = dict(legacy.get("data", {}))
                        if "title" in legacy:
                            state.setdefault("window_title", legacy["title"])
                        records.append({
                            "type": "measure_table",
                            "state": state,
                        })

                factories = {
                    "oscilloscope": self.new_scope,
                    "measure_table": self.new_measure_table,
                    "scalar_table": self.new_scalar_table,
                }
                for record in records:
                    if not isinstance(record, dict):
                        continue
                    factory = factories.get(record.get("type"))
                    if factory is None:
                        continue
                    widget = factory()
                    widget.import_state(record.get("state", {}))

        except Exception:
            pass
        
    ###########################
    # OscilloscopeWidget widget
    ###########################
    def on_scope_closed(self, widget):
        if widget in self.mOslScopeWidgets:
            self.mOslScopeWidgets.remove(widget)

    def new_scope(self):
        w = OscilloscopeWidgetV2.OscilloscopeWidgetV2(self.data_manager)
        self.mdiArea.addSubWindow(w)
        self.worker.signal_ready.connect(w.on_xcp_data)
        self.mOslScopeWidgets.append(w)
        w.closed.connect(self.on_scope_closed)
        w.show()
        return w

    ###########################
    # ScalarTableWidget widget
    ###########################

    def new_scalar_table(self):
        table = ScalarTableWidget.ScalarTableWidget(self.data_manager)
        self.mdiArea.addSubWindow(table)
        self.mScalarTableWidgets.append(table)
        table.closed.connect(self.on_scalar_closed)
        table.show()
        return table

    def on_scalar_closed(self, widget):
        if widget in self.mScalarTableWidgets:
            self.mScalarTableWidgets.remove(widget)

    ###########################
    # MeasureTableWidget widget
    ###########################
    def on_measure_closed(self, widget):
        if widget in self.mMeasureTableWidgets:
            self.mMeasureTableWidgets.remove(widget)

    def new_measure_table(self) -> MeasureTableWidget:
        w = MeasureTableWidget.MeasureTableWidget(self.data_manager)
        self.mdiArea.addSubWindow(w)
        # Connect worker to this scope
        # TODO Cleanup this self.worker.data_received.connect(w.update_value)
        self.mMeasureTableWidgets.append(w)
        w.closed.connect(self.on_measure_closed)
        w.show()
        return w
    
    def close_active_window(self):
        sub = self.mdiArea.activeSubWindow()
        if sub:
            sub.close()

    def start_acquisition(self):
        if not self.worker.isRunning():
            self.worker.start()
            for widget in self.mMeasureTableWidgets:
                widget.start()
            for w in self.mOslScopeWidgets:
                w.start()
    def stop_acquisition(self):
        if self.worker.isRunning():
            self.worker.stop()
            for widget in self.mMeasureTableWidgets:
                widget.stop()
            for w in self.mOslScopeWidgets:
                w.stop()

    
    def refresh_all_widgets(self):
        for sub in self.mdiArea.subWindowList():
            # Check subwindow visibility
            if not sub.isVisible() or sub.isMinimized():
                continue
            try:
                sub.refresh_widgets()
            except Exception as e:
                print(f"Refresh error: {e}")

    # --------------------------------------------------
    # CLEAN EXIT
    # --------------------------------------------------
    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
        event.accept()
        self.save_project()

# ==========================================================
# 4. APPLICATION ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    pg.setConfigOptions(antialias=True)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
