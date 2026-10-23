from datetime import datetime

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    run_id: str
    format: str = Field("html", pattern="^(html|pdf|both)$")


class ReportGenerateResponse(BaseModel):
    message: str
    run_id: str
    format: str


class ReportResponse(BaseModel):
    id: str
    run_id: str
    user_id: str
    format: str
    html_path: str | None
    pdf_path: str | None
    generated_at: datetime
    file_size_bytes: int


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int
    page: int
    page_size: int
