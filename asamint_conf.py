c = get_config()  # noqa

# Minimal project configuration
c.General.project     = "MyProject"
c.General.a2l_file    = r"C:\eclipse_wp\Project_BCU\Debug\Project_BCU.exe.a2l"
c.General.master_hexfile      = r"C:\eclipse_wp\Project_BCU\Debug\Project_BCU.exe.hex"
c.General.master_hexfile_type = "ihex"   # or "srec"

# Optional: link an existing pyxcp config for online (hardware) use
c.General.pyxcp_config_file = "pyxcp_conf.py"
