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
from app.config import get_settings
from app.db.repositories import spec_repository, test_case_repository
from app.db.mongo import get_collection
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

    settings = get_settings()
    provider = settings.ai_primary_provider
    model = settings.default_model_for(provider)
    await get_collection("api_specs").update_one(
        {"_id": obj_id, "user_id": user_id},
        {"$set": {"test_generation_status": "running", "test_generation_error": None}},
    )

    async def run_generation() -> None:
        orchestrator = GenerationOrchestrator()
        try:
            outcome = await orchestrator.generate_for_spec(
                spec_id=obj_id,
                user_id=user_id,
                categories=categories,
                prompt_version=request.prompt_version,
                dry_run=request.dry_run,
                model=model,
            )
            status_value = "completed_with_errors" if outcome.get("failed", 0) else "completed"
            await get_collection("api_specs").update_one(
                {"_id": obj_id},
                {"$set": {
                    "test_generation_status": status_value,
                    "test_generation_error": "; ".join(outcome.get("errors", [])) or None,
                }},
            )
        except Exception as exc:
            logger.exception("Test case generation failed", spec_id=spec_id)
            await get_collection("api_specs").update_one(
                {"_id": obj_id},
                {"$set": {"test_generation_status": "failed", "test_generation_error": str(exc)}},
            )
        finally:
            await orchestrator.close()

    background_tasks.add_task(run_generation)

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
    generation = await get_collection("api_specs").find_one(
        {"_id": obj_id}, {"test_generation_status": 1, "test_generation_error": 1}
    ) or {}

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
        generation_status=generation.get("test_generation_status"),
        generation_error=generation.get("test_generation_error"),
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
