from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pyqtgraph as pg

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QToolBar, QInputDialog, QColorDialog
)
from PyQt6.QtGui import QColor

from ui.WidgetBase import WidgetBase

# ============================================================
# Ring buffer
# ============================================================
class RingBuffer:
    """
    Fixed-size numpy ring buffer for x/y signal data.
    Optimized for real-time append + periodic redraw.
    """
    def __init__(self, capacity: int):
        self.capacity = max(1, int(capacity))
        self.x = np.empty(self.capacity, dtype=np.float64)
        self.y = np.empty(self.capacity, dtype=np.float64)
        self.size = 0
        self.write_idx = 0

    def clear(self):
        self.size = 0
        self.write_idx = 0

    def append(self, x_value: float, y_value: float):
        self.x[self.write_idx] = x_value
        self.y[self.write_idx] = y_value
        self.write_idx = (self.write_idx + 1) % self.capacity
        if self.size < self.capacity:
            self.size += 1

    def is_empty(self) -> bool:
        return self.size == 0

    def last_value(self) -> float:
        if self.size == 0:
            return 0.0
        idx = (self.write_idx - 1) % self.capacity
        return float(self.y[idx])

    def min_max(self):
        if self.size == 0:
            return 0.0, 0.0
        y = self.get_y_view()
        return float(np.min(y)), float(np.max(y))

    def get_x_view(self) -> np.ndarray:
        if self.size == 0:
            return np.empty(0, dtype=np.float64)

        if self.size < self.capacity:
            return self.x[:self.size]

        # wrapped: return logical order
        return np.concatenate((self.x[self.write_idx:], self.x[:self.write_idx]))

    def get_y_view(self) -> np.ndarray:
        if self.size == 0:
            return np.empty(0, dtype=np.float64)

        if self.size < self.capacity:
            return self.y[:self.size]

        return np.concatenate((self.y[self.write_idx:], self.y[:self.write_idx]))

    def get_xy_view(self):
        return self.get_x_view(), self.get_y_view()


# ============================================================
# Signal state
# ============================================================
@dataclass
class SignalState:
    name: str
    color: str
    vb: pg.ViewBox
    curve: pg.PlotDataItem
    buffer: RingBuffer
    visible: bool = True
    dirty: bool = False


# ============================================================
# Multi-signal plot
# ============================================================
class MultiSignalPlot(pg.PlotWidget):
    """
    Shared scope:
    - all signals shown together on one screen
    - each signal has its own ViewBox (independent Y scale)
    - all ViewBoxes share the same X axis
    - selected signal supports Y-only zoom/pan
    """

    ZOOM_IN_FACTOR = 0.85
    ZOOM_OUT_FACTOR = 1.15
    FINE_ZOOM_IN_FACTOR = 0.92
    FINE_ZOOM_OUT_FACTOR = 1.08
    PAN_STEP_RATIO = 0.08

    def __init__(self, parent=None):
        plot_item = pg.PlotItem()
        super().__init__(parent=parent, plotItem=plot_item)

        self._plot_item = plot_item
        self._main_vb = plot_item.vb

        self.setBackground('#083c4a')
        self.showGrid(x=True, y=True, alpha=0.22)

        self._plot_item.setLabel('bottom', 'Time (s)')
        self._plot_item.setLabel('left', 'Value')

        self.left_axis = self._plot_item.getAxis('left')

        if self._main_vb is not None:
            self._main_vb.setMouseEnabled(x=True, y=False)
            self._main_vb.sigResized.connect(self._update_viewboxes)

        self.signals: Dict[str, SignalState] = {}
        self.selected_name: Optional[str] = None

    # --------------------------------------------------------
    # Safe base ViewBox access
    # --------------------------------------------------------
    def _base_viewbox(self):
        vb = getattr(self, "_main_vb", None)
        if vb is not None:
            return vb

        plot_item = getattr(self, "_plot_item", None)
        if plot_item is not None:
            return getattr(plot_item, "vb", None)

        return None

    def _update_viewboxes(self):
        base_vb = self._base_viewbox()
        if base_vb is None:
            return

        rect = base_vb.sceneBoundingRect()

        for sig in self.signals.values():
            sig.vb.setGeometry(rect)
            sig.vb.linkedViewChanged(base_vb, sig.vb.XAxis)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._update_viewboxes()

    # --------------------------------------------------------
    # Signal management
    # --------------------------------------------------------
    def add_signal(self, name: str, color: str, max_points: int = 5000):
        if name in self.signals:
            return

        base_vb = self._base_viewbox()
        if base_vb is None:
            return

        vb = pg.ViewBox(enableMouse=False)
        vb.setXLink(base_vb)
        self.scene().addItem(vb)

        curve = pg.PlotDataItem([], [], pen=pg.mkPen(color=color, width=2))
        # Performance helpers
        curve.setClipToView(True)
        curve.setDownsampling(auto=True, method='peak')

        vb.addItem(curve)

        sig = SignalState(
            name=name,
            color=color,
            vb=vb,
            curve=curve,
            buffer=RingBuffer(max_points),
            visible=True,
            dirty=False,
        )
        self.signals[name] = sig

        self._update_viewboxes()

        if self.selected_name is None:
            self.select_signal(name)

    def remove_signal(self, name: str):
        sig = self.signals.pop(name, None)
        if sig is None:
            return

        if self.selected_name == name:
            next_name = next(iter(self.signals), None)
            self.selected_name = None
            if next_name is None:
                self.left_axis.linkToView(self._main_vb)
                self.left_axis.setLabel(text="Value")
            else:
                self.select_signal(next_name)

        sig.vb.clear()
        self.scene().removeItem(sig.vb)

    def append_sample(self, name: str, x: float, y: float):
        sig = self.signals.get(name)
        if sig is None:
            return

        sig.buffer.append(x, y)
        sig.dirty = True

        # Initial Y range setup when first samples arrive
        if sig.buffer.size == 1:
            sig.vb.setYRange(y - 1.0, y + 1.0, padding=0)
        elif sig.buffer.size == 2:
            ymin, ymax = sig.buffer.min_max()
            margin = max((ymax - ymin) * 0.10, 1.0)
            sig.vb.setYRange(ymin - margin, ymax + margin, padding=0)

    def redraw_dirty_curves(self):
        """
        Redraw only visible and dirty signals.
        Call this at a lower fixed FPS than sample ingestion.
        """
        for sig in self.signals.values():
            if not sig.visible or not sig.dirty:
                continue

            x_arr, y_arr = sig.buffer.get_xy_view()
            sig.curve.setData(x_arr, y_arr)
            sig.dirty = False

    def clear_all_data(self):
        for sig in self.signals.values():
            sig.buffer.clear()
            sig.curve.setData([], [])
            sig.vb.setYRange(-1.0, 1.0, padding=0)
            sig.dirty = False

    def set_signal_visible(self, name: str, visible: bool):
        sig = self.signals.get(name)
        if sig is None:
            return

        sig.visible = visible
        sig.curve.setVisible(visible)

    def set_x_window(self, xmin: float, xmax: float):
        base_vb = self._base_viewbox()
        if base_vb is None:
            return
        base_vb.setXRange(xmin, xmax, padding=0)

    # --------------------------------------------------------
    # Selection
    # --------------------------------------------------------
    def _apply_curve_style(self, sig: SignalState, selected: bool):
        if selected:
            sig.curve.setPen(pg.mkPen(color=sig.color, width=3))
            sig.curve.setZValue(10)
        else:
            sig.curve.setPen(pg.mkPen(color=sig.color, width=1.5))
            sig.curve.setZValue(0)

    def select_signal(self, name: str):
        if name not in self.signals:
            return

        if self.selected_name == name:
            return

        old_name = self.selected_name
        self.selected_name = name

        if old_name is not None and old_name in self.signals:
            self._apply_curve_style(self.signals[old_name], selected=False)

        self._apply_curve_style(self.signals[name], selected=True)

        selected_sig = self.signals[name]
        self.left_axis.linkToView(selected_sig.vb)
        self.left_axis.setLabel(text=f"Value — {name}")

        axis_pen = pg.mkPen(selected_sig.color, width=1.5)
        self.left_axis.setPen(axis_pen)
        self.left_axis.setTextPen(axis_pen)

    # --------------------------------------------------------
    # Selected signal Y controls
    # --------------------------------------------------------
    def scale_selected_y(self, factor: float):
        if self.selected_name is None:
            return

        sig = self.signals[self.selected_name]
        (_, _), (ymin, ymax) = sig.vb.viewRange()

        center = (ymin + ymax) / 2.0
        half_span = (ymax - ymin) / 2.0 * factor
        half_span = max(half_span, 1e-9)

        sig.vb.setYRange(center - half_span, center + half_span, padding=0)

    def pan_selected_y(self, dy_ratio: float = 0.10):
        if self.selected_name is None:
            return

        sig = self.signals[self.selected_name]
        (_, _), (ymin, ymax) = sig.vb.viewRange()

        span = ymax - ymin
        delta = span * dy_ratio
        sig.vb.setYRange(ymin + delta, ymax + delta, padding=0)

    def auto_fit_selected_y(self):
        if self.selected_name is None:
            return

        sig = self.signals[self.selected_name]
        if sig.buffer.is_empty():
            return

        ymin, ymax = sig.buffer.min_max()
        margin = max((ymax - ymin) * 0.10, 1.0)
        sig.vb.setYRange(ymin - margin, ymax + margin, padding=0)

    # --------------------------------------------------------
    # Mouse interaction
    # --------------------------------------------------------
    def wheelEvent(self, ev):
        if self.selected_name is None:
            super().wheelEvent(ev)
            return

        delta = ev.angleDelta().y()
        if delta == 0:
            ev.accept()
            return

        modifiers = ev.modifiers()

        # Shift + wheel => pan selected signal on Y
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            if delta > 0:
                self.pan_selected_y(-self.PAN_STEP_RATIO)
            else:
                self.pan_selected_y(+self.PAN_STEP_RATIO)
            ev.accept()
            return

        # Ctrl + wheel => fine zoom
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            zoom_in = self.FINE_ZOOM_IN_FACTOR
            zoom_out = self.FINE_ZOOM_OUT_FACTOR
        else:
            zoom_in = self.ZOOM_IN_FACTOR
            zoom_out = self.ZOOM_OUT_FACTOR

        if delta > 0:
            self.scale_selected_y(zoom_in)
        else:
            self.scale_selected_y(zoom_out)

        ev.accept()


# ============================================================
# Main window
# ============================================================
class OscilloscopeWidgetV2(WidgetBase):
    """
    Performance-optimized real-time shared scope.
    """

    SAMPLE_INTERVAL_MS = 20         # data generation / ingestion rate (50 Hz)
    RENDER_INTERVAL_MS = 33         # redraw rate (~30 FPS)
    TABLE_INTERVAL_MS = 100         # table refresh rate (10 FPS)
    WINDOW_SECONDS = 10.0
    # Bound memory while retaining the full visible ten-second window at 50 Hz.
    MAX_POINTS = 5000

    def __init__(self, data_manager, parent=None):
        super().__init__(data_manager, parent)
        self.plot = MultiSignalPlot()
        self._setup_toolbar()

        # ==================================================
        # CENTRAL AREA (PLOT + TABLE)
        # ==================================================
        self._center_layout = QHBoxLayout()
        self._setup_ui()
        self.plot.set_x_window(0.0, self.WINDOW_SECONDS)
        self._main_layout.addLayout(self._center_layout)

        self.current_time = 0.0
        self.is_scope_running = False

        self.signal_defs = []
        self.signal_row_map: Dict[str, int] = {}
        
    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------
    def _setup_ui(self):
 
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_layout.removeWidget(self._table_widget)
        # Insert a new column at the beginning
        self._table_widget.insertColumn(0)
        # Set header
        self._table_widget.setHorizontalHeaderItem(0, QTableWidgetItem("Vis"))
        self._table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table_widget.itemChanged.connect(self._on_table_item_changed)
        self._table_widget.selectionModel().selectionChanged.connect(self._on_selection_changed)

        splitter.addWidget(self.plot)
        splitter.addWidget(self._table_widget)
        splitter.setSizes([980, 300])

        self._center_layout.addWidget(splitter)
        self.setWindowTitle("Oscilloscope")

    def _setup_toolbar(self):
        tb = QToolBar("Scope Toolbar")
        #self.addToolBar(tb)
        self._main_layout.addWidget(tb)

        act_run = tb.addAction("Run")
        act_pause = tb.addAction("Pause")
        act_reset = tb.addAction("Reset")
        tb.addSeparator()

        act_zoom_in = tb.addAction("Y+")
        act_zoom_out = tb.addAction("Y-")
        act_pan_up = tb.addAction("↑Y")
        act_pan_down = tb.addAction("↓Y")
        act_fit = tb.addAction("Fit Y")

        act_run.triggered.connect(self.start_acquisition)
        act_pause.triggered.connect(self.stop_acquisition)
        act_reset.triggered.connect(self.reset_acquisition)

        act_zoom_in.triggered.connect(lambda: self.plot.scale_selected_y(0.85))
        act_zoom_out.triggered.connect(lambda: self.plot.scale_selected_y(1.15))
        act_pan_up.triggered.connect(lambda: self.plot.pan_selected_y(-0.08))
        act_pan_down.triggered.connect(lambda: self.plot.pan_selected_y(+0.08))
        act_fit.triggered.connect(self.plot.auto_fit_selected_y)

    def _add_signal_row(self, name: str, value: float):
        row = self._table_widget.rowCount()
        self._table_widget.insertRow(row)

        vis_item = QTableWidgetItem("")
        vis_item.setCheckState(Qt.CheckState.Checked)
        vis_item.setFlags(
            Qt.ItemFlag.ItemIsEnabled |
            Qt.ItemFlag.ItemIsSelectable |
            Qt.ItemFlag.ItemIsUserCheckable
        )

        name_item = QTableWidgetItem(name)
        value_item = QTableWidgetItem(f"{value:.3f}")

        self._table_widget.setItem(row, 0, vis_item)
        self._table_widget.setItem(row, 1, name_item)
        self._table_widget.setItem(row, 2, value_item)

        self.signal_row_map[name] = row

    def _signal_name_column(self):
        return 1

    def _signal_value_column(self):
        return 2

    def add_item(self):
        name, accepted = QInputDialog.getText(
            self,
            "Add plot signal",
            "Signal name:",
        )
        name = name.strip()
        if not accepted or not name or name in self.plot.signals:
            return

        color = QColorDialog.getColor(QColor("#ffffff"), self, "Signal color")
        if not color.isValid():
            return

        self.acquire_signal(name)
        self.signal_defs.append({"name": name, "color": color.name()})
        self.plot.add_signal(name, color.name(), max_points=self.MAX_POINTS)
        self._table_widget.blockSignals(True)
        self._add_signal_row(name, 0.0)
        self._table_widget.blockSignals(False)

    def remove_selected_item(self):
        row = self._table_widget.currentRow()
        if row < 0:
            return

        name_item = self._table_widget.item(row, self._signal_name_column())
        if name_item is None:
            return

        name = name_item.text()
        self._table_widget.removeRow(row)
        self.signal_row_map = {
            self._table_widget.item(index, self._signal_name_column()).text(): index
            for index in range(self._table_widget.rowCount())
            if self._table_widget.item(index, self._signal_name_column()) is not None
        }
        self.signal_defs = [signal for signal in self.signal_defs if signal["name"] != name]
        self.plot.remove_signal(name)
        self.release_signal(name)

    def export_state(self):
        state = super().export_state()
        state["signals"] = [
            {
                "name": signal["name"],
                "color": signal["color"],
                "visible": self.plot.signals[signal["name"]].visible,
            }
            for signal in self.signal_defs
            if signal["name"] in self.plot.signals
        ]
        return state

    def import_state(self, state):
        if not isinstance(state, dict):
            return

        super().import_state(state)

        for name in tuple(self.plot.signals):
            self.plot.remove_signal(name)
        for name in tuple(self._owned_signals):
            self.release_signal(name)

        self.signal_defs = []
        self.signal_row_map.clear()
        self._table_widget.setRowCount(0)

        for signal in state.get("signals", []):
            if not isinstance(signal, dict):
                continue
            name = str(signal.get("name", "")).strip()
            color = str(signal.get("color", "#ffffff"))
            if not name or name in self.plot.signals:
                continue

            self.acquire_signal(name)
            self.signal_defs.append({"name": name, "color": color})
            self.plot.add_signal(name, color, max_points=self.MAX_POINTS)
            self._add_signal_row(name, 0.0)
            visible = bool(signal.get("visible", True))
            self.plot.set_signal_visible(name, visible)
            visibility_item = self._table_widget.item(
                self._table_widget.rowCount() - 1,
                0,
            )
            if visibility_item is not None:
                visibility_item.setCheckState(
                    Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked
                )

        if self._table_widget.rowCount() > 0:
            self._table_widget.selectRow(0)
            self.plot.select_signal(self._table_widget.item(0, 1).text())

    # --------------------------------------------------------
    # Real-time pipeline
    # --------------------------------------------------------
    @pyqtSlot(tuple)
    def on_xcp_data(self, sample):
        """Receive one worker sample on the GUI thread."""
        if not self.is_scope_running:
            return

        timestamp, name, value = sample
        state = self.plot.signals.get(name)
        if state is None:
            return

        timestamp = float(timestamp)
        self.current_time = max(self.current_time, timestamp)
        self.plot.append_sample(name, timestamp, float(value))

        row = self.signal_row_map.get(name)
        if row is not None:
            item = self._table_widget.item(row, 2)
            if item is not None:
                item.setText(f"{float(value):.3f}")

    def refresh_data(self):
        if not self.is_scope_running:
            return
        self.render_scope()


    def render_scope(self):
        if not self.is_scope_running:
            return

        self.plot.redraw_dirty_curves()

        xmin = max(0.0, self.current_time - self.WINDOW_SECONDS)
        xmax = max(self.WINDOW_SECONDS, self.current_time)
        self.plot.set_x_window(xmin, xmax)

    # --------------------------------------------------------
    # Controls
    # --------------------------------------------------------
    def start_acquisition(self):
        self.reset_acquisition()
        self.is_scope_running = True
    
    def stop_acquisition(self):
        self.is_scope_running = False

    def reset_acquisition(self):
        self.is_scope_running = False
        self.current_time = 0.0

        self.plot.clear_all_data()

        for row in range(self._table_widget.rowCount()):
            value_item = self._table_widget.item(row, 2)
            if value_item is not None:
                value_item.setText("0.000")

        self.plot.set_x_window(0.0, self.WINDOW_SECONDS)
        self.is_scope_running = True

    # --------------------------------------------------------
    # Table interaction
    # --------------------------------------------------------
    def _on_table_item_changed(self, item):
        if item.column() != 0:
            return

        row = item.row()
        name_item = self._table_widget.item(row, 1)
        if name_item is None:
            return

        name = name_item.text()
        visible = item.checkState() == Qt.CheckState.Checked
        self.plot.set_signal_visible(name, visible)

    def _on_selection_changed(self):
        row = self._table_widget.currentRow()
        if row < 0:
            return

        name_item = self._table_widget.item(row, 1)
        if name_item is None:
            return

        self.plot.select_signal(name_item.text())

    # --------------------------------------------------------
    # Safe shutdown
    # --------------------------------------------------------
    def closeEvent(self, event):
        for timer_name in ("sample_timer", "render_timer", "table_timer"):
            timer = getattr(self, timer_name, None)
            if timer is not None and timer.isActive():
                timer.stop()

        super().closeEvent(event)
