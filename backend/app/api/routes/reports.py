import os

import structlog
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUserId
from app.api.schemas.reports import (
    ReportGenerateRequest,
    ReportGenerateResponse,
    ReportListResponse,
    ReportResponse,
)
from app.db.repositories import report_repository, run_repository
from app.reports.generator import ReportGenerator

logger = structlog.get_logger()

router = APIRouter()


@router.post("", response_model=ReportGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_report(
    user_id: CurrentUserId,
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
):
    try:
        run_obj_id = ObjectId(request.run_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    run = await run_repository.get_by_id(run_obj_id, user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in ("completed", "completed_with_errors"):
        raise HTTPException(status_code=400, detail="Run must be in a reportable terminal state")

    generator = ReportGenerator()
    background_tasks.add_task(generator.generate, run_obj_id, user_id, request.format)

    return {"message": "Report generation started", "run_id": request.run_id, "format": request.format}


@router.get("", response_model=ReportListResponse)
async def list_reports(
    user_id: CurrentUserId,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    skip = (page - 1) * page_size
    reports = await report_repository.list_by_user(user_id, skip, page_size)
    total = await report_repository.collection.count_documents({"user_id": user_id})

    return ReportListResponse(
        reports=[
            ReportResponse(
                id=str(r.id),
                run_id=str(r.run_id),
                user_id=str(r.user_id),
                format=r.format,
                html_path=r.html_path,
                pdf_path=r.pdf_path,
                generated_at=r.generated_at,
                file_size_bytes=r.file_size_bytes,
            )
            for r in reports
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, user_id: CurrentUserId):
    try:
        obj_id = ObjectId(report_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid report ID")

    report = await report_repository.get_by_id(obj_id)
    if not report or report.user_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse(
        id=str(report.id),
        run_id=str(report.run_id),
        user_id=str(report.user_id),
        format=report.format,
        html_path=report.html_path,
        pdf_path=report.pdf_path,
        generated_at=report.generated_at,
        file_size_bytes=report.file_size_bytes,
    )


@router.get("/{report_id}/download")
async def download_report(report_id: str, user_id: CurrentUserId, format: str = Query("html", pattern="^(html|pdf)$")):
    try:
        obj_id = ObjectId(report_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid report ID")

    report = await report_repository.get_by_id(obj_id)
    if not report or report.user_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")

    file_path = report.html_path if format == "html" else report.pdf_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found")

    media_type = "text/html" if format == "html" else "application/pdf"
    filename = os.path.basename(file_path)

    return FileResponse(path=file_path, media_type=media_type, filename=filename)


@router.get("/runs/{run_id}", response_model=ReportResponse)
async def get_latest_report_for_run(run_id: str, user_id: CurrentUserId):
    try:
        run_obj_id = ObjectId(run_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    run = await run_repository.get_by_id(run_obj_id, user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    report = await report_repository.get_by_run(run_obj_id)
    if not report:
        raise HTTPException(status_code=404, detail="No report found for this run")

    return ReportResponse(
        id=str(report.id),
        run_id=str(report.run_id),
        user_id=str(report.user_id),
        format=report.format,
        html_path=report.html_path,
        pdf_path=report.pdf_path,
        generated_at=report.generated_at,
        file_size_bytes=report.file_size_bytes,
    )
