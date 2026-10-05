from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


class ExtractionError(Exception):
    """The file could not be understood at all."""


@dataclass
class ExtractedLine:
    sku: str | None
    description: str | None
    quantity: Decimal | None
    unit_price: Decimal | None
    row: int | None = None


@dataclass
class ExtractedInvoice:
    invoice_number: str | None
    party_name: str | None
    invoice_date: date | None
    due_date: date | None
    lines: list[ExtractedLine] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)   # problems found while parsing
    rows: list[int] = field(default_factory=list)     # source rows, for CSV error reporting


class InvoiceExtractor(ABC):
    """Turns an uploaded document into candidate invoices. Never writes to the database."""

    name: str
    extensions: tuple[str, ...]

    @abstractmethod
    def extract(self, data: bytes) -> list[ExtractedInvoice]: ...
