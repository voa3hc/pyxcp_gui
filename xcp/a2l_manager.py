from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from asamint.asam import open_a2l_database
from pya2l.model import Measurement


@dataclass(frozen=True)
class MeasurementInfo:
    """Stable application-facing metadata for one A2L measurement."""

    name: str
    description: str
    datatype: str | None
    conversion: str | None
    unit: str | None
    address: int | None
    address_extension: int | None
    lower_limit: float | None
    upper_limit: float | None


class A2lManager:
    """Load and query the measurements defined by an ASAM A2L file."""

    def __init__(self, a2l_path: str | Path):
        self.a2l_path = Path(a2l_path).expanduser()
        self._database: Any | None = None

    @property
    def is_loaded(self) -> bool:
        return self._database is not None

    def load(self) -> None:
        """Open the configured A2L file and build its local parser database."""
        if not self.a2l_path.is_file():
            raise FileNotFoundError(f"A2L file not found: {self.a2l_path}")

        self.close()
        self._database = open_a2l_database(str(self.a2l_path))

    def close(self) -> None:
        """Close the parser session and release its database resources."""
        if self._database is None:
            return

        close = getattr(self._database, "close", None)
        if close is not None:
            close()
        self._database = None

    def __enter__(self) -> "A2lManager":
        self.load()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def list_measurements(self) -> list[MeasurementInfo]:
        """Return all A2L measurements ordered by their symbolic name."""
        session = self._require_session()
        measurements = session.query(Measurement).order_by(Measurement.name).all()
        return [self._to_measurement_info(measurement) for measurement in measurements]

    def get_measurement(self, name: str) -> MeasurementInfo | None:
        """Return one measurement by exact symbolic name, or ``None``."""
        session = self._require_session()
        measurement = session.query(Measurement).filter(Measurement.name == name).first()
        if measurement is None:
            return None
        return self._to_measurement_info(measurement)

    def search_measurements(self, text: str) -> list[MeasurementInfo]:
        """Find measurements whose names contain ``text`` case-insensitively."""
        query = text.casefold()
        return [
            measurement
            for measurement in self.list_measurements()
            if query in measurement.name.casefold()
        ]

    def _require_session(self):
        if self._database is None:
            raise RuntimeError("A2L database is not loaded; call load() first")
        return self._database._session

    @staticmethod
    def _to_measurement_info(measurement: Measurement) -> MeasurementInfo:
        ecu_address = getattr(measurement, "ecu_address", None)
        address = getattr(ecu_address, "address", None)
        address_extension = getattr(measurement, "ecu_address_extension", None)
        unit = getattr(getattr(measurement, "phys_unit", None), "unit", None)

        return MeasurementInfo(
            name=measurement.name,
            description=measurement.longIdentifier or "",
            datatype=measurement.datatype,
            conversion=measurement.conversion,
            unit=unit,
            address=address,
            address_extension=address_extension,
            lower_limit=measurement.lowerLimit,
            upper_limit=measurement.upperLimit,
        )
