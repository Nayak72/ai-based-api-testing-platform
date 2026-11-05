from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.models import ResultStorageIntegrity, RunSummary, TestRunCreate, TestRunInDB
from app.db.mongo import get_collection


class RunRepository:
    def __init__(self):
        self._collection: AsyncIOMotorCollection | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            self._collection = get_collection("test_runs")
        return self._collection

    async def create(self, run: TestRunCreate, user_id: ObjectId) -> TestRunInDB:
        now = datetime.now(UTC)
        doc = {
            **run.model_dump(),
            "user_id": user_id,
            "status": "pending",
            "summary": RunSummary().model_dump(),
            "result_integrity": ResultStorageIntegrity().model_dump(),
            "owasp_coverage": [],
            "started_at": None,
            "completed_at": None,
            "created_at": now,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return TestRunInDB(**doc)

    async def get_by_id(self, run_id: ObjectId, user_id: ObjectId) -> TestRunInDB | None:
        doc = await self.collection.find_one({"_id": run_id, "user_id": user_id})
        return TestRunInDB(**doc) if doc else None

    async def list_by_user(
        self,
        user_id: ObjectId,
        skip: int = 0,
        limit: int = 20,
        spec_id: ObjectId | None = None,
        status: str | None = None,
    ) -> list[TestRunInDB]:
        query = {"user_id": user_id}
        if spec_id:
            query["spec_id"] = spec_id
        if status:
            query["status"] = status
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return [TestRunInDB(**doc) async for doc in cursor]

    async def count_by_user(self, user_id: ObjectId, spec_id: ObjectId | None = None, status: str | None = None) -> int:
        query = {"user_id": user_id}
        if spec_id:
            query["spec_id"] = spec_id
        if status:
            query["status"] = status
        return await self.collection.count_documents(query)

    async def update_status(self, run_id: ObjectId, status: str) -> TestRunInDB | None:
        now = datetime.now(UTC)
        update = {"status": status, "updated_at": now}
        if status == "running":
            update["started_at"] = now
        elif status in ("completed", "completed_with_errors", "failed", "cancelled"):
            update["completed_at"] = now
        result = await self.collection.find_one_and_update({"_id": run_id}, {"$set": update}, return_document=True)
        return TestRunInDB(**result) if result else None

    async def increment_summary(self, run_id: ObjectId, field: str, amount: int = 1) -> None:
        await self.collection.update_one({"_id": run_id}, {"$inc": {f"summary.{field}": amount}})

    async def replace_summary(self, run_id: ObjectId, summary: RunSummary) -> None:
        await self.collection.update_one({"_id": run_id}, {"$set": {"summary": summary.model_dump()}})

    async def set_duration(self, run_id: ObjectId, duration_seconds: float) -> None:
        await self.collection.update_one({"_id": run_id}, {"$set": {"summary.duration_seconds": duration_seconds}})

    async def reconcile_results(
        self,
        run_id: ObjectId,
        *,
        selected_count: int,
        executed_count: int,
        persisted_count: int,
        summary_count: int,
        insertion_errors: int = 0,
        last_error: str | None = None,
    ) -> None:
        if insertion_errors and persisted_count == 0:
            integrity_status = "failed"
        elif insertion_errors or persisted_count < executed_count:
            integrity_status = "partially_persisted"
        elif persisted_count != summary_count:
            integrity_status = "inconsistent"
        else:
            integrity_status = "valid"
        await self.collection.update_one(
            {"_id": run_id},
            {"$set": {"result_integrity": {
                "status": integrity_status,
                "selected_count": selected_count,
                "executed_count": executed_count,
                "persisted_count": persisted_count,
                "summary_count": summary_count,
                "last_error": last_error,
                "reconciled_at": datetime.now(UTC),
            }}},
        )

    async def update_started_at(self, run_id: ObjectId) -> None:
        await self.collection.update_one({"_id": run_id}, {"$set": {"started_at": datetime.now(UTC)}})

    async def update_completed_at(self, run_id: ObjectId) -> None:
        await self.collection.update_one({"_id": run_id}, {"$set": {"completed_at": datetime.now(UTC)}})

    async def update_config(self, run_id: ObjectId, config) -> TestRunInDB | None:
        result = await self.collection.find_one_and_update(
            {"_id": run_id}, {"$set": {"config": config.model_dump()}}, return_document=True
        )
        return TestRunInDB(**result) if result else None


run_repository = RunRepository()
