from ui.MeasureTableWidget import MeasureTableWidget

class ScalarTableWidget(MeasureTableWidget):
    
    def __init__(self, data_manager, parent=None):
        super().__init__(data_manager, parent)
        # optional
        self.setWindowTitle("Scalar Table")
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

    
