# ECU Instrumentation Suite

A PyQt6-based GUI application for real-time ECU (Engine Control Unit) instrumentation, data acquisition, and calibration using the XCP (Universal Measurement and Calibration Protocol).

## Overview

The ECU Instrumentation Suite provides a comprehensive graphical interface for:
- **Real-time data acquisition** from ECU via XCP protocol
- **Data visualization** using oscilloscope and scalar display widgets
- **Measurements and logging** with configurable DAQ lists
- **Multi-window MDI interface** for simultaneous monitoring of multiple data streams
- **A2L metadata support** for automatic signal definition and memory mapping

## Project Structure

```
pyxcp_gui/
├── pyxcp_gui_app.py           # Main application entry point (MDI window)
├── pyxcp_conf.py              # pyXCP protocol configuration
├── asamint_conf.py            # A2L file and project configuration
├── engine_dynamics.csv        # Sample engine parameter data
├── requirements.txt           # Python dependencies
├── recent.exp                 # Recently opened project state
├── ui/                        # UI Widgets and components
│   ├── OscilloscopeWidgetV2.py # Real-time waveform visualization
│   ├── ScalarTableWidget.py    # Scalar value display table
│   ├── MeasureTableWidget.py   # Measurement statistics table
│   ├── OscilloscopeWidget.py   # Legacy oscilloscope widget
│   ├── WidgetBase.py           # Base class for all widgets
│   └── test_scope.py           # Oscilloscope widget tests
└── xcp/                       # XCP protocol and data management
    ├── XcpWorker.py           # XCP communication worker thread
    └── DataManager.py         # Central data state management
```

## Features

### Data Acquisition & Management
- **DAQ Lists**: Configure 10ms and 100ms sampling rates
- **Hardware Timestamps**: Synchronized timestamp capture from ECU
- **Thread-safe Data Manager**: Lock-based concurrent access to signal data
- **CSV Export**: Convert DAQ data to CSV format

### Visualization Widgets
- **OscilloscopeWidget**: Real-time waveform plotting with zoom/pan controls
- **ScalarTableWidget**: Live tabular display of parameter values
- **MeasureTableWidget**: Statistical analysis and measurement summaries

### Multi-Window Interface
- MDI (Multiple Document Interface) for simultaneous data stream monitoring
- Independent widget scaling and positioning
- Project state persistence (recent.exp)

### Protocol Support
- **XCP (CAN/Ethernet)**: Universal Measurement and Calibration Protocol
- **A2L Support**: ASAM metadata for signal definitions
- **pyXCP Library**: Industry-standard XCP implementation

## Dependencies

- **PyQt6** (6.11.0) - GUI framework
- **PyQt6-Qt6** (6.11.1) - Qt bindings
- **pyqtgraph** (0.14.0) - Scientific graphics
- **pyserial** (3.5) - Serial communication
- **python-can** (4.6.1) - CAN bus interface
- **asamint** - ASAM metadata integration

Install all dependencies:
```bash
pip install -r requirements.txt
```

## Setup & Configuration

### 1. Configure Project Settings
Edit `asamint_conf.py`:
```python
c.General.project = "YourProject"
c.General.a2l_file = "/path/to/your/project.a2l"
c.General.master_hexfile = "/path/to/your/firmware.hex"
c.General.pyxcp_config_file = "pyxcp_conf.py"
```

### 2. Configure XCP Connection
Edit `pyxcp_conf.py` for your XCP transport layer (CAN, Ethernet, etc.)

### 3. Define DAQ Lists
Modify `xcp/XcpWorker.py` to configure measurement parameters:
```python
DAQ_LISTS = [
    DaqList(
        name="DAQ_10MS",
        event_num=1,
        stim=False,
        enable_timestamps=True,
        measurements=[
            ("Signal_Name", 0x10000000, 0, "U8"),
        ]
    ),
]
```

## Running the Application

```bash
python pyxcp_gui_app.py
```

The application will:
1. Load the A2L file and project configuration
2. Initialize the XCP connection
3. Start the data acquisition worker thread
4. Display the main MDI window with available widgets

## Architecture

### Threading Model
- **Main Thread**: GUI event loop and widget updates
- **Worker Thread**: XCP communication and data polling (XcpWorker)
- **Thread-safe Communication**: DataManager uses locks and Qt signals

### Data Flow
```
ECU (via XCP)
    ↓
XcpWorker (background thread)
    ↓
DataManager (thread-safe storage with signals)
    ↓
UI Widgets (pull snapshots on refresh timers)
```

### Component Roles
- **XcpWorker**: Manages XCP protocol communication, DAQ sampling
- **DataManager**: Central repository for signal values, thread-safe access
- **UI Widgets**: Independent refresh cycles, snapshot-based rendering
- **MainWindow**: MDI container, widget management, project persistence

## Key Classes

| Class | Purpose |
|-------|---------|
| `MainWindow` | MDI application container, window management |
| `XcpWorker` | XCP protocol handler, background data acquisition |
| `DataManager` | Central signal storage, thread-safe access |
| `OscilloscopeWidgetV2` | Real-time waveform visualization |
| `ScalarTableWidget` | Live parameter table display |
| `MeasureTableWidget` | Measurement statistics and logging |

## Project State

The application automatically saves and restores:
- Recent project configuration in `recent.exp`
- Window layout and widget positions
- DAQ list state and sampling rates

## Extensibility

To add new widgets:
1. Extend `WidgetBase` class
2. Implement snapshot-based data retrieval from DataManager
3. Add widget creation to MainWindow menu

To add new data sources:
1. Extend XcpWorker or create alternative worker
2. Update DataManager signal definitions
3. Connect to the `data_arrived` signal

## License & Attribution

This project uses:
- **pyXCP**: ASAM standard XCP implementation
- **PyQt6**: Cross-platform GUI framework
- **pyqtgraph**: Scientific graphics library

## Support & Troubleshooting

### Connection Issues
- Verify XCP transport layer configuration (CAN bus, Ethernet, serial)
- Check A2L file path and format
- Confirm ECU is running and responsive

### Performance
- Adjust DAQ sampling rates in XcpWorker
- Reduce widget refresh rates for slower systems
- Check system resources and thread priorities

### Data Quality
- Verify signal address mappings in A2L file
- Enable timestamps for synchronization
- Review DAQ list configuration for conflicts

---

**Last Updated**: 2026-07-10
**Version**: 1.0
