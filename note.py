import asamint
print(asamint.__version__)
import time

from pyxcp.cmdline import ArgumentParser
from pyxcp.daq_stim import DaqList, DaqToCsv, DaqOnlinePolicy
import struct

# 1. Subclass the LoggingPolicy to intercept raw incoming DAQ packets
class ConsolePrintPolicy(DaqOnlinePolicy):
    def __init__(self, daq_lists):
        # Pass the desired DAQ layout configuration up to the parent engine
        super().__init__(daq_lists)

    def on_daq_list(self, daq_list: int, timestamp0: int, timestamp1: int, payload: list):
        # Example processing loop: Extract variables by matching DAQ List ID
    
        # Assume data contains a 4-byte Float (e.g., Engine Speed) at byte index 0
        print(f"daq_list: {daq_list}, timestamp0: {timestamp0}, timestamp1: {timestamp1}, payload: {payload}")


def test_function():
    ap = ArgumentParser(description="Continuous DAQ Measurement")

    # 1. Define the continuous measurement plan (DAQ list)
    # Addresses are mapped directly from your A2L memory file metadata
    DAQ_LISTS = [
        DaqList(
            name="engine_dynamics",
            event_num=1,             # References the ECU's 10ms task loop
            stim=False,              # False = Data Acquisition (DAQ) mode
            enable_timestamps=True,  # Embed ECU hardware clock timestamps
            measurements=[
                ("TestVar_u8", 0x10000000, 0, "U8"),  # Name, hex address, ext, type
                ("TestVar_C_u8", 0x20000000, 0, "U8")
            ]
        )
    ]

    # 2. Use the streaming policy to write directly to a CSV format
    daq_recorder = DaqToCsv(DAQ_LISTS)
    printer_policy = ConsolePrintPolicy(DAQ_LISTS)

    # 3. Establish session framework and stream data continuously
    with ap.run(policy=printer_policy) as xcp_master:
        xcp_master.connect()
        xcp_master.cond_unlock("DAQ") # Release DAQ resources if locked
        
        print("Configuring DAQ lists and subscribing to ECU task threads...")
        printer_policy.setup()
        
        print("Beginning continuous data transmission...")
        printer_policy.start()
        
        # Keep the script alive for 30 seconds to stream data frames
        time.sleep(5)
        
        print("Stopping continuous stream safely...")
        printer_policy.stop()
        xcp_master.close()
        #xcp_master.disconnect()

from pyxcp import master
from pyxcp.config import (  # noqa: F401
    create_application,
    get_application,
    reset_application,
)

# 1. Define the continuous measurement plan (DAQ list)
# Addresses are mapped directly from your A2L memory file metadata
DAQ_LISTS = [
    DaqList(
        name="engine_dynamics",
        event_num=2,             # References the ECU's 10ms task loop
        stim=False,              # False = Data Acquisition (DAQ) mode
        enable_timestamps=True,  # Embed ECU hardware clock timestamps
        measurements=[
            ("TestVar_u8", 0x10000000, 0, "U8"),  # Name, hex address, ext, type
            ("TestVar_C_u8", 0x20000000, 0, "U8")
        ]
    )
]


printer_policy = ConsolePrintPolicy(DAQ_LISTS)

ap = ArgumentParser(description="Continuous DAQ Measurement")
# 3. Establish session framework and stream data continuously
with ap.run(policy=printer_policy) as xcp_master:
    xcp_master.connect()
    xcp_master.cond_unlock("DAQ") # Release DAQ resources if locked

    print("Configuring DAQ lists and subscribing to ECU task threads...")
    printer_policy.setup()

    print("Beginning continuous data transmission...")
    printer_policy.start()


    time.sleep(1)  # 10 ms event channel

    print("Stopping continuous stream safely...")
    printer_policy.stop()
    xcp_master.close()