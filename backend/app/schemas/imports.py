from pydantic import BaseModel


class RowError(BaseModel):
    row: int
    errors: list[str]
    data: dict[str, str]


class ImportPreview(BaseModel):
    kind: str
    total_rows: int
    valid_rows: int
    error_rows: int
    errors: list[RowError]


class ImportResult(ImportPreview):
    imported: int
