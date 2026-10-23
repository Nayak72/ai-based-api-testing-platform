import structlog
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.api.deps import CurrentUserId
from app.api.schemas.runs import (
    ResultListResponse,
    ResultResponse,
    RunConfigSchema,
    RunCreateRequest,
    RunListResponse,
    RunResponse,
    RunSummarySchema,
)
from app.db.repositories import result_repository, run_repository, spec_repository
from app.executor.runner import RunOrchestrator

logger = structlog.get_logger()

router = APIRouter()


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    user_id: CurrentUserId,
    request: RunCreateRequest,
    background_tasks: BackgroundTasks,
):
    try:
        spec_obj_id = ObjectId(request.spec_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid spec ID")

    spec = await spec_repository.get_by_id(spec_obj_id, user_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    if spec.status != "ready":
        raise HTTPException(status_code=400, detail="Spec not ready for execution")

    config = request.config or RunConfigSchema()
    run_create = RunCreateRequest(
        spec_id=request.spec_id,
        name=request.name,
        config=config,
    )

    run = await run_repository.create(run_create, user_id)

    orchestrator = RunOrchestrator()
    background_tasks.add_task(orchestrator.execute_run, str(run.id), str(user_id))

    logger.info("Run created", run_id=str(run.id), user_id=str(user_id), spec_id=request.spec_id)

    return RunResponse(
        id=str(run.id),
        spec_id=str(run.spec_id),
        user_id=str(run.user_id),
        name=run.name,
        trigger=run.trigger,
        status=run.status,
        config=RunConfigSchema(**run.config.model_dump()),
        summary=RunSummarySchema(**run.summary.model_dump()),
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
    )


@router.get("", response_model=RunListResponse)
async def list_runs(
    user_id: CurrentUserId,
    spec_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    spec_obj_id = ObjectId(spec_id) if spec_id else None
    skip = (page - 1) * page_size
    runs = await run_repository.list_by_user(user_id, skip, page_size, spec_obj_id, status_filter)
    total = await run_repository.count_by_user(user_id, spec_obj_id, status_filter)

    return RunListResponse(
        runs=[
            RunResponse(
                id=str(r.id),
                spec_id=str(r.spec_id),
                user_id=str(r.user_id),
                name=r.name,
                trigger=r.trigger,
                status=r.status,
                config=RunConfigSchema(**r.config.model_dump()),
                summary=RunSummarySchema(**r.summary.model_dump()),
                started_at=r.started_at,
                completed_at=r.completed_at,
                created_at=r.created_at,
            )
            for r in runs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, user_id: CurrentUserId):
    try:
        obj_id = ObjectId(run_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    run = await run_repository.get_by_id(obj_id, user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunResponse(
        id=str(run.id),
        spec_id=str(run.spec_id),
        user_id=str(run.user_id),
        name=run.name,
        trigger=run.trigger,
        status=run.status,
        config=RunConfigSchema(**run.config.model_dump()),
        summary=RunSummarySchema(**run.summary.model_dump()),
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
    )


@router.get("/{run_id}/results", response_model=ResultListResponse)
async def list_results(
    run_id: str,
    user_id: CurrentUserId,
    status_filter: str | None = Query(None, alias="status"),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    try:
        run_obj_id = ObjectId(run_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    run = await run_repository.get_by_id(run_obj_id, user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    skip = (page - 1) * page_size
    results = await result_repository.list_by_run(run_obj_id, status_filter, category, skip, page_size)
    total = await result_repository.count_by_run(run_obj_id, status_filter, category)

    return ResultListResponse(
        results=[
            ResultResponse(
                id=str(r.id),
                run_id=str(r.run_id),
                test_case_id=str(r.test_case_id),
                endpoint_id=r.endpoint_id,
                category=r.category,
                status=r.status,
                request_sent=r.request_sent.model_dump(),
                response=r.response.model_dump(),
                assertions=[a.model_dump() for a in r.assertions],
                error=r.error,
                llm_analysis=r.llm_analysis.model_dump() if r.llm_analysis else None,
                retried=r.retried,
                attempt=r.attempt,
                created_at=r.created_at,
            )
            for r in results
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{run_id}/results/{result_id}", response_model=ResultResponse)
async def get_result(run_id: str, result_id: str, user_id: CurrentUserId):
    try:
        run_obj_id = ObjectId(run_id)
        result_obj_id = ObjectId(result_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")

    run = await run_repository.get_by_id(run_obj_id, user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    result = await result_repository.get_by_id(result_obj_id)
    if not result or result.run_id != run_obj_id:
        raise HTTPException(status_code=404, detail="Result not found")

    return ResultResponse(
        id=str(result.id),
        run_id=str(result.run_id),
        test_case_id=str(result.test_case_id),
        endpoint_id=result.endpoint_id,
        category=result.category,
        status=result.status,
        request_sent=result.request_sent.model_dump(),
        response=result.response.model_dump(),
        assertions=[a.model_dump() for a in result.assertions],
        error=result.error,
        llm_analysis=result.llm_analysis.model_dump() if result.llm_analysis else None,
        retried=result.retried,
        attempt=result.attempt,
        created_at=result.created_at,
    )


@router.post("/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(run_id: str, user_id: CurrentUserId):
    try:
        obj_id = ObjectId(run_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    run = await run_repository.get_by_id(obj_id, user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel run in status: {run.status}")

    orchestrator = RunOrchestrator()
    await orchestrator.cancel_run(obj_id)

    run = await run_repository.get_by_id(obj_id, user_id)
    return RunResponse(
        id=str(run.id),
        spec_id=str(run.spec_id),
        user_id=str(run.user_id),
        name=run.name,
        trigger=run.trigger,
        status=run.status,
        config=RunConfigSchema(**run.config.model_dump()),
        summary=RunSummarySchema(**run.summary.model_dump()),
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
    )


@router.post("/{run_id}/retry-failed", response_model=RunResponse)
async def retry_failed(
    run_id: str,
    user_id: CurrentUserId,
    background_tasks: BackgroundTasks,
):
    try:
        obj_id = ObjectId(run_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    run = await run_repository.get_by_id(obj_id, user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail=f"Cannot retry run in status: {run.status}")

    orchestrator = RunOrchestrator()
    background_tasks.add_task(orchestrator.retry_failed, obj_id)

    run = await run_repository.get_by_id(obj_id, user_id)
    return RunResponse(
        id=str(run.id),
        spec_id=str(run.spec_id),
        user_id=str(run.user_id),
        name=run.name,
        trigger=run.trigger,
        status=run.status,
        config=RunConfigSchema(**run.config.model_dump()),
        summary=RunSummarySchema(**run.summary.model_dump()),
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
    )


@router.post("/{run_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_run(run_id: str, user_id: CurrentUserId, background_tasks: BackgroundTasks):
    try:
        obj_id = ObjectId(run_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    run = await run_repository.get_by_id(obj_id, user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status != "completed":
        raise HTTPException(status_code=400, detail="Run must be completed to analyze")

    from app.analyzer.engine import ResultAnalyzer
    analyzer = ResultAnalyzer()
    background_tasks.add_task(analyzer.analyze_run, obj_id)

    return {"message": "Analysis started", "run_id": run_id}
