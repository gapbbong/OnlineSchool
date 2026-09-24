from typing import List, Optional

from pydantic import BaseModel


class BulkImportRowResult(BaseModel):
    row: int
    name: Optional[str] = None
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


class BulkImportResponse(BaseModel):
    total_rows: int
    succeeded: int
    failed: int
    results: List[BulkImportRowResult]
