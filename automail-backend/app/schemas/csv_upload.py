from __future__ import annotations

import uuid

from pydantic import BaseModel


class CSVValidationError(BaseModel):
    row_number: int
    error: str
    raw_data: dict[str, str]


class CSVUploadResponse(BaseModel):
    campaign_id: uuid.UUID
    total_rows: int
    valid_leads: int
    invalid_leads: int
    validation_errors: list[CSVValidationError]
