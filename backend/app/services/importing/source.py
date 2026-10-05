from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceRow:
    """One raw record from an external system, before validation."""
    row: int                 # 1-based position in the source (CSV: line number incl. header)
    data: dict[str, str]


class AccountingSource(ABC):
    """Boundary between VyapaarOS and an external accounting system.

    Implementations only fetch and normalise raw records into flat string dicts using the
    VyapaarOS import column names. Validation and persistence live in ImportService, so a new
    source (e.g. Tally) never touches business rules. See docs/integrations/tally.md.
    """

    @abstractmethod
    def get_customers(self) -> list[SourceRow]: ...

    @abstractmethod
    def get_products(self) -> list[SourceRow]: ...

    @abstractmethod
    def get_invoices(self) -> list[SourceRow]: ...

    @abstractmethod
    def get_payments(self) -> list[SourceRow]: ...
