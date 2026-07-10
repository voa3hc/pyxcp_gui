import asamint
print(f"asamint's version: : {asamint.__version__}")
import time
from pyxcp.cmdline import ArgumentParser
from pyxcp.daq_stim import DaqList, DaqToCsv, DaqOnlinePolicy
import struct
import math
import random
from PyQt6.QtCore import QThread, pyqtSignal

# 1. Define the continuous measurement plan (DAQ list)
# Addresses are mapped directly from your A2L memory file metadata
DAQ_10MS = 0
DAQ_100MS = 1

DAQ_LISTS = [
    DaqList(
        name="DAQ_10MS",
        event_num=1,             # References the ECU's 10ms task loop
        stim=False,              # False = Data Acquisition (DAQ) mode
        enable_timestamps=True,  # Embed ECU hardware clock timestamps
        measurements=[
            ("TestVar1_u8", 0x10000000, 0, "U8"),  # Name, hex address, ext, type
        ]
    ),
    DaqList(
        name="DAQ_100MS",
        event_num=2,             # References the ECU's 100ms task loop, TODO review this
        stim=False,              # False = Data Acquisition (DAQ) mode
        enable_timestamps=True,  # Embed ECU hardware clock timestamps
        measurements=[
            ("TestVar2_u8", 0x10000001, 0, "U8")
        ]
    )
]


# Subclass the UpdateDataToDataManager to intercept raw incoming DAQ packets
class UpdateDataToDataManager(DaqOnlinePolicy):
    def __init__(self, daq_lists, callback=None):
        # Pass the desired DAQ layout configuration up to the parent engine
        super().__init__(daq_lists)
        self._callback = callback
        self._t0 = time.perf_counter()

    def on_daq_list(self, daq_list: int, timestamp0: int, timestamp1: int, payload: list):
        #print(f"daq_list: {daq_list}, timestamp0: {timestamp0}, timestamp1: {timestamp1}, delta: {timestamp1 - timestamp0} payload: {payload}")
        daq = DAQ_LISTS[daq_list]
        measurements = daq.measurements
        #import pdb; pdb.set_trace()
        # --- OPTION A: use host time ---
        t = time.perf_counter() - self._t0
        
        if self._callback is not None:
            idx = 0
            for measurement in measurements:
                self._callback(t, measurement.name, float(payload[idx]))
                idx = idx + 1

class XcpWorker(QThread):
    
    signal_ready = pyqtSignal(tuple)  # (name, value, timestamp)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
    
    def on_sample(self, timestamp: float, name: str, value: float):
        self.signal_ready.emit((timestamp, name, value))

    def run(self):
        self._running = True
        
        policy = UpdateDataToDataManager(DAQ_LISTS, self.on_sample)
        
        ap = ArgumentParser()
        # Establish session framework and stream data continuously
        with ap.run(policy=policy) as xcp_master:
            xcp_master.connect()
            xcp_master.cond_unlock("DAQ") # Release DAQ resources if locked
            
            print("Configuring DAQ lists and subscribing to ECU task threads...")
            policy.setup()
            
            print("Beginning continuous data transmission...")
            policy.start()
            
            while self._running:
                time.sleep(1)
            
            print("Stopping continuous stream safely...")
            policy.stop()
            try:
                xcp_master.close()
            except Exception:
                    pass
        # End with
    
    def stop(self):
        print("Stopping continuous stream safely...")
        self._running = False
        self.wait()

