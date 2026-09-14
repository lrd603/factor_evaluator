"""Historical index membership provider with strict PIT requirements."""

from .csv_provider import CSVUniverseProvider


class IndexConstituentProvider(CSVUniverseProvider):
    """Require dated membership intervals; never backfill current constituents."""

    def get_universe(self, date: object, universe_name: str = "CSI300") -> list[str]:
        if universe_name.upper() == "ALL_A":
            raise ValueError("IndexConstituentProvider supports CSI300/CSI500 only")
        return super().get_universe(date, universe_name)
