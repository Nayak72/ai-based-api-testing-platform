import structlog
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.api.deps import CurrentUserId
from app.api.schemas.test_cases import (
    TestCaseGenerateRequest,
    TestCaseListResponse,
    TestCaseResponse,
    TestCaseUpdateRequest,
)
from app.db.repositories import spec_repository, test_case_repository, user_repository
from app.generators.orchestrator import GenerationOrchestrator

logger = structlog.get_logger()

router = APIRouter()


@router.post("/{spec_id}/test-cases/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_test_cases(
    spec_id: str,
    user_id: CurrentUserId,
    request: TestCaseGenerateRequest,
    background_tasks: BackgroundTasks,
):
    try:
        obj_id = ObjectId(spec_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid spec ID")

    spec = await spec_repository.get_by_id(obj_id, user_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    if spec.status != "ready":
        raise HTTPException(status_code=400, detail="Spec not ready for generation")

    categories = request.categories or ["functional", "edge", "malformed", "security"]

    user = await user_repository.get_by_id(user_id)
    user_ai = getattr(user, "ai_settings", {}) or {} if user else {}
    provider = request.provider or user_ai.get("primary_provider")
    model = request.model or user_ai.get("default_model")
    api_key = request.api_key or (
        user_ai.get("nim_api_key") if provider == "nim" else user_ai.get("openrouter_api_key")
    )

    orchestrator = GenerationOrchestrator(
        primary_provider=provider,
        model=model,
        api_key=api_key,
    )
    background_tasks.add_task(
        orchestrator.generate_for_spec,
        spec_id=obj_id,
        user_id=user_id,
        categories=categories,
        prompt_version=request.prompt_version,
        dry_run=request.dry_run,
        model=model,
    )

    return {
        "message": "Test generation started",
        "spec_id": spec_id,
        "categories": categories,
        "model": model,
        "provider": provider,
    }


@router.get("/{spec_id}/test-cases", response_model=TestCaseListResponse)
async def list_test_cases(
    spec_id: str,
    user_id: CurrentUserId,
    endpoint_id: str | None = Query(None),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    try:
        obj_id = ObjectId(spec_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid spec ID")

    spec = await spec_repository.get_by_id(obj_id, user_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    skip = (page - 1) * page_size
    test_cases = await test_case_repository.list_by_spec(obj_id, endpoint_id, category, skip, page_size)
    total = await test_case_repository.count_by_spec(obj_id, endpoint_id, category)

    return TestCaseListResponse(
        test_cases=[
            TestCaseResponse(
                id=str(tc.id),
                spec_id=str(tc.spec_id),
                endpoint_id=tc.endpoint_id,
                category=tc.category,
                subcategory=tc.subcategory,
                title=tc.title,
                description=tc.description,
                request=tc.request,
                expected=tc.expected,
                metadata=tc.metadata,
                created_at=tc.created_at,
            )
            for tc in test_cases
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{spec_id}/test-cases/{test_case_id}", response_model=TestCaseResponse)
async def get_test_case(spec_id: str, test_case_id: str, user_id: CurrentUserId):
    try:
        spec_obj_id = ObjectId(spec_id)
        tc_obj_id = ObjectId(test_case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")

    spec = await spec_repository.get_by_id(spec_obj_id, user_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    tc = await test_case_repository.get_by_id(tc_obj_id)
    if not tc or tc.spec_id != spec_obj_id:
        raise HTTPException(status_code=404, detail="Test case not found")

    return TestCaseResponse(
        id=str(tc.id),
        spec_id=str(tc.spec_id),
        endpoint_id=tc.endpoint_id,
        category=tc.category,
        subcategory=tc.subcategory,
        title=tc.title,
        description=tc.description,
        request=tc.request,
        expected=tc.expected,
        metadata=tc.metadata,
        created_at=tc.created_at,
    )


@router.patch("/{spec_id}/test-cases/{test_case_id}", response_model=TestCaseResponse)
async def update_test_case(spec_id: str, test_case_id: str, user_id: CurrentUserId, request: TestCaseUpdateRequest):
    try:
        spec_obj_id = ObjectId(spec_id)
        tc_obj_id = ObjectId(test_case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")

    spec = await spec_repository.get_by_id(spec_obj_id, user_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    tc = await test_case_repository.get_by_id(tc_obj_id)
    if not tc or tc.spec_id != spec_obj_id:
        raise HTTPException(status_code=404, detail="Test case not found")

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    from datetime import datetime
    update_data["updated_at"] = datetime.now()

    result = await test_case_repository.collection.find_one_and_update(
        {"_id": tc_obj_id}, {"$set": update_data}, return_document=True
    )

    return TestCaseResponse(
        id=str(result["_id"]),
        spec_id=str(result["spec_id"]),
        endpoint_id=result["endpoint_id"],
        category=result["category"],
        subcategory=result["subcategory"],
        title=result["title"],
        description=result["description"],
        request=result["request"],
        expected=result["expected"],
        metadata=result["metadata"],
        created_at=result["created_at"],
    )


@router.delete("/{spec_id}/test-cases/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_case(spec_id: str, test_case_id: str, user_id: CurrentUserId):
    try:
        spec_obj_id = ObjectId(spec_id)
        tc_obj_id = ObjectId(test_case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")

    spec = await spec_repository.get_by_id(spec_obj_id, user_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    tc = await test_case_repository.get_by_id(tc_obj_id)
    if not tc or tc.spec_id != spec_obj_id:
        raise HTTPException(status_code=404, detail="Test case not found")

    await test_case_repository.delete(tc_obj_id)
    logger.info("Test case deleted", test_case_id=test_case_id, user_id=str(user_id))
