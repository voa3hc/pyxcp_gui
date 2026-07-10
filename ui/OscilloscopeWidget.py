
import collections
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QWidgetAction,
    QTableWidget,QTableWidgetItem,
    QTableWidgetItem, QHeaderView, QToolBar, QHBoxLayout
)
from PyQt6.QtGui import QColor, QBrush
import pyqtgraph as pg

from ui.MeasurementBase import MeasurementBase
from ui.WidgetBase import WidgetBase
# ==========================================================
# OSCILLOSCOPE WIDGET
# ==========================================================

class OscilloscopeWidget(WidgetBase, MeasurementBase):
    """
        Oscilloscope widget with:
        - real-time plotting
        - auto-scroll (follow latest time)
        - keeps follow mode even after zoom in/out on X axis,
        as long as the view stays near the newest sample
        """

    def __init__(self, parent=None, time_window=10.0, max_points=5000):
        super().__init__(parent)
        MeasurementBase.__init__(self)
        
        # central widget
        self._central = QWidget()
        self.setWidget(self._central)
                
        self.running = True

        main_layout = QVBoxLayout(self._central)

        # ==================================================
        # TOOLBAR
        # ==================================================
        toolbar = QToolBar()

        self.start_action = QWidgetAction(self)
        self.start_action.setText("Start")
        self.start_action.triggered.connect(self.start)

        self.stop_action = QWidgetAction(self)
        self.stop_action.setText("Stop")
        self.stop_action.triggered.connect(self.stop)

        self.clear_action = QWidgetAction(self)
        self.clear_action.setText("Clear")
        self.clear_action.triggered.connect(self.clear)
        

        toolbar.addAction(self.start_action)
        toolbar.addAction(self.stop_action)
        toolbar.addAction(self.clear_action)

        main_layout.addWidget(toolbar)

        # ==================================================
        # CENTRAL AREA (PLOT + TABLE)
        # ==================================================
        center_layout = QHBoxLayout()

        # ------------------ Plot ------------------
        self.plot = pg.PlotWidget()
        self.plot.setBackground("#0b3a4a")  # dark blue like INCA
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setLabel("left", "Value")
        self.plot.setLabel("bottom", "Time", "s")

        # NEW START
        # Plot configuration
        self.plot.showGrid(x=True, y=True, alpha=0.3)

        self.plot.addLegend()
        self.plot.setLabel("bottom", "Time", units="s")
        self.plot.setLabel("left", "Value")
        self.plot.setMouseEnabled(x=True, y=True)

        # Buffers per signal
        self._buffers = {}   # name -> {"t": deque, "y": deque}
        self._curves = {}    # name -> PlotDataItem

        # Auto-scroll / follow-tail state
        self._default_time_window = float(time_window)
        self._max_points = int(max_points)
        self._latest_t = 0.0

        # True = keep right edge locked to latest sample
        self._follow_tail = True

        # If viewport right edge is close enough to latest_t,
        # keep follow-tail ON even after zooming.
        self._follow_threshold_ratio = 0.10  # 10% of visible width

        self._color_index = 0
        self._palette = [
            "#ffcc00", "#00d0ff", "#ff5c8a", "#6aff6a",
            "#b388ff", "#ff8c42", "#00e5a8", "#ffffff"
        ]

        # Track manual pan/zoom changes
        self.plot.getViewBox().sigXRangeChanged.connect(self._on_xrange_changed)

        # NEW END

        center_layout.addWidget(self.plot, 3)

        # ------------------ Signal Table ------------------
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Style", "Name", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumWidth(250)

        center_layout.addWidget(self.table, 1)

        main_layout.addLayout(center_layout)

        # Add default signal
        self.add_signal("TestVar_u8")


    # ==================================================
    # CONTROLS
    # ==================================================
    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def clear(self):
        pass

    # --------------------------------------------------
    def _next_pen(self):
        color = self._palette[self._color_index % len(self._palette)]
        self._color_index += 1
        return pg.mkPen(color=color, width=2)

    # --------------------------------------------------
    def add_signal(self, name: str):
        """Register a new signal curve if it does not exist yet."""
        if name in self._curves:
            return

        self._buffers[name] = {
            "t": collections.deque(maxlen=self._max_points),
            "y": collections.deque(maxlen=self._max_points),
        }
        self._curves[name] = self.plot.plot(
            [],
            [],
            pen=self._next_pen(),
            name=name
        )

        if name not in self.mMeasurementList:
            self.mMeasurementList.append(name)

    # --------------------------------------------------
    def remove_signal(self, name: str):
        """Optional helper to remove a signal curve."""
        if name in self._curves:
            self.plot.removeItem(self._curves[name])
            del self._curves[name]

        if name in self._buffers:
            del self._buffers[name]

        if name in self.mMeasurementList:
            self.mMeasurementList.remove(name)

    # --------------------------------------------------
    def clear_data(self):
        """Clear all plotted samples but keep the registered curves."""
        self._latest_t = 0.0
        for name in self._buffers:
            self._buffers[name]["t"].clear()
            self._buffers[name]["y"].clear()
            self._curves[name].setData([], [])

        self.plot.setXRange(0, self._default_time_window, padding=0)
        self._follow_tail = True

    # --------------------------------------------------
    def set_follow_tail(self, enabled: bool):
        """Force enable / disable auto-scroll mode."""
        self._follow_tail = bool(enabled)
        if self._follow_tail:
            self.scroll_to_latest()

    # --------------------------------------------------
    def scroll_to_latest(self):
        """Snap the view so the right edge follows the newest sample."""
        vb = self.plot.getViewBox()
        x_min, x_max = vb.viewRange()[0]
        visible_width = max(0.001, x_max - x_min)

        if self._latest_t <= visible_width:
            vb.setXRange(0.0, visible_width, padding=0)
        else:
            vb.setXRange(self._latest_t - visible_width, self._latest_t, padding=0)

    # --------------------------------------------------
    def _on_xrange_changed(self, view_box, x_range):
        """
        Decide whether the user is still 'near the tail'.

        If the right edge remains close to the newest sample,
        keep follow-tail ON even after zoom in/out.
        If the user pans away to inspect history, disable follow-tail.
        """
        x_min, x_max = x_range
        visible_width = max(0.001, x_max - x_min)
        threshold = visible_width * self._follow_threshold_ratio

        # If the current right edge is close to latest_t, still follow.
        self._follow_tail = (self._latest_t - x_max) <= threshold

    # --------------------------------------------------
    def update_value(self, name: str, t: float, value: float):
        """
        Append one sample and refresh the curve.
        Auto-scroll uses the CURRENT visible width, so if the user
        zooms in/out on X while still near the latest sample,
        the chart continues scrolling with that zoom level preserved.
        """
        if name not in self._curves:
            self.add_signal(name)

        buf = self._buffers[name]
        buf["t"].append(float(t))
        buf["y"].append(float(value))

        self._curves[name].setData(list(buf["t"]), list(buf["y"]))

        if t > self._latest_t:
            self._latest_t = float(t)

        if self._follow_tail:
            vb = self.plot.getViewBox()
            x_min, x_max = vb.viewRange()[0]
            visible_width = max(0.001, x_max - x_min)

            # First-time / default fallback
            if visible_width <= 0.001:
                visible_width = self._default_time_window

            if self._latest_t <= visible_width:
                vb.setXRange(0.0, visible_width, padding=0)
            else:
                vb.setXRange(self._latest_t - visible_width, self._latest_t, padding=0)

    # --------------------------------------------------
    def export_state(self):
        """
        Save basic widget + viewport state.
        """
        vb = self.plot.getViewBox()
        x_range, y_range = vb.viewRange()

        return {
            "geometry": {
                "x": self.x(),
                "y": self.y(),
                "width": self.width(),
                "height": self.height(),
            },
            "signals": list(self._curves.keys()),
            "x_range": [x_range[0], x_range[1]],
            "y_range": [y_range[0], y_range[1]],
            "follow_tail": self._follow_tail,
            "default_time_window": self._default_time_window,
            "max_points": self._max_points,
        }

    # --------------------------------------------------
    def import_state(self, state):
        """
        Restore basic widget + viewport state.
        """
        geo = state.get("geometry")
        if geo:
            self.resize(geo.get("width", 700), geo.get("height", 400))
            self.move(geo.get("x", 100), geo.get("y", 100))

        for name in state.get("signals", []):
            self.add_signal(name)

        self._follow_tail = state.get("follow_tail", True)
        self._default_time_window = state.get("default_time_window", 10.0)
        self._max_points = state.get("max_points", 5000)

        x_range = state.get("x_range")
        y_range = state.get("y_range")

        vb = self.plot.getViewBox()
        if x_range and len(x_range) == 2:
            vb.setXRange(float(x_range[0]), float(x_range[1]), padding=0)
        if y_range and len(y_range) == 2:
            vb.setYRange(float(y_range[0]), float(y_range[1]), padding=0)
