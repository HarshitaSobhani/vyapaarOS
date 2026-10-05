from typing import Annotated, Literal

from fastapi import APIRouter, File, UploadFile

from app.api.deps import DB, Approver, CurrentUser, Today
from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.imports import ImportPreview, ImportResult
from app.services.importing.csv_source import CSVAccountingSource
from app.services.importing.service import ImportService

router = APIRouter(prefix="/imports", tags=["imports"])
Kind = Literal["customers", "products", "invoices", "payments"]


async def _read(file: UploadFile) -> bytes:
    limit = get_settings().max_upload_bytes
    if not (file.filename or "").lower().endswith(".csv"):
        raise AppError("Upload a .csv file", 415, "unsupported_file")
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise AppError("File is too large", 413, "file_too_large")
    return data


@router.post("/{kind}/preview", response_model=ImportPreview)
async def preview(kind: Kind, db: DB, _: CurrentUser, today: Today, file: Annotated[UploadFile, File()]) -> ImportPreview:
    return ImportService(db, CSVAccountingSource(**{kind: await _read(file)}), today).preview(kind)


@router.post("/{kind}/commit", response_model=ImportResult)
async def commit(kind: Kind, db: DB, _: Approver, today: Today, file: Annotated[UploadFile, File()]) -> ImportResult:
    return ImportService(db, CSVAccountingSource(**{kind: await _read(file)}), today).commit(kind)
