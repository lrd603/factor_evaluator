"""Common contracts and metadata for historical universe providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass


SUPPORTED_UNIVERSES = {"CSI300", "CSI500", "ALL_A"}


@dataclass(frozen=True)
class UniverseMetadata:
    """Auditable quality metadata for a universe source."""

    universe_source: str
    point_in_time_universe: bool
    historical_constituents_available: bool
    survivorship_bias_status: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        """Return JSON-serializable metadata."""
        result = asdict(self); result["warnings"] = list(self.warnings); return result


class UniverseProvider(ABC):
    """Interface for resolving a named stock universe at a historical date."""

    metadata: UniverseMetadata

    @abstractmethod
    def get_universe(self, date: object, universe_name: str = "ALL_A") -> list[str]:
        """Return codes known to belong to ``universe_name`` on ``date``."""
