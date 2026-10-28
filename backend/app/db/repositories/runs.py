from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.models import RunSummary, TestRunCreate, TestRunInDB
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
        now = datetime.now()
        doc = {
            **run.model_dump(),
            "user_id": user_id,
            "status": "pending",
            "summary": RunSummary().model_dump(),
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
        update = {"status": status, "updated_at": datetime.now()}
        if status == "running":
            update["started_at"] = datetime.now()
        elif status in ("completed", "completed_with_errors", "failed", "cancelled"):
            update["completed_at"] = datetime.now()
        result = await self.collection.find_one_and_update({"_id": run_id}, {"$set": update}, return_document=True)
        return TestRunInDB(**result) if result else None

    async def increment_summary(self, run_id: ObjectId, field: str, amount: int = 1) -> None:
        await self.collection.update_one({"_id": run_id}, {"$inc": {f"summary.{field}": amount}})

    async def set_duration(self, run_id: ObjectId, duration_seconds: float) -> None:
        await self.collection.update_one({"_id": run_id}, {"$set": {"summary.duration_seconds": duration_seconds}})

    async def update_started_at(self, run_id: ObjectId) -> None:
        await self.collection.update_one({"_id": run_id}, {"$set": {"started_at": datetime.now()}})

    async def update_completed_at(self, run_id: ObjectId) -> None:
        await self.collection.update_one({"_id": run_id}, {"$set": {"completed_at": datetime.now()}})

    async def update_config(self, run_id: ObjectId, config) -> TestRunInDB | None:
        result = await self.collection.find_one_and_update(
            {"_id": run_id}, {"$set": {"config": config.model_dump()}}, return_document=True
        )
        return TestRunInDB(**result) if result else None


run_repository = RunRepository()
