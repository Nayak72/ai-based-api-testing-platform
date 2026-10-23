from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.models import TestResultBase, TestResultInDB
from app.db.mongo import get_collection


class ResultRepository:
    def __init__(self):
        self._collection: AsyncIOMotorCollection | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            self._collection = get_collection("test_results")
        return self._collection

    async def create(self, result: TestResultBase) -> TestResultInDB:
        doc = result.model_dump(by_alias=True)
        doc["created_at"] = datetime.now()
        result_insert = await self.collection.insert_one(doc)
        doc["_id"] = result_insert.inserted_id
        return TestResultInDB(**doc)

    async def bulk_create(self, results: list[TestResultBase]) -> int:
        if not results:
            return 0
        docs = [r.model_dump(by_alias=True) for r in results]
        for doc in docs:
            doc["created_at"] = datetime.now()
        result = await self.collection.insert_many(docs)
        return len(result.inserted_ids)

    async def get_by_id(self, result_id: ObjectId) -> TestResultInDB | None:
        doc = await self.collection.find_one({"_id": result_id})
        return TestResultInDB(**doc) if doc else None

    async def list_by_run(
        self,
        run_id: ObjectId,
        status: str | None = None,
        category: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TestResultInDB]:
        query = {"run_id": run_id}
        if status:
            query["status"] = status
        if category:
            query["category"] = category
        cursor = self.collection.find(query).sort("created_at", 1).skip(skip).limit(limit)
        return [TestResultInDB(**doc) async for doc in cursor]

    async def count_by_run(self, run_id: ObjectId, status: str | None = None, category: str | None = None) -> int:
        query = {"run_id": run_id}
        if status:
            query["status"] = status
        if category:
            query["category"] = category
        return await self.collection.count_documents(query)

    async def update_analysis(self, result_id: ObjectId, analysis: dict) -> TestResultInDB | None:
        result = await self.collection.find_one_and_update(
            {"_id": result_id}, {"$set": {"llm_analysis": analysis}}, return_document=True
        )
        return TestResultInDB(**result) if result else None

    async def update_status(self, result_id: ObjectId, status: str) -> TestResultInDB | None:
        result = await self.collection.find_one_and_update(
            {"_id": result_id}, {"$set": {"status": status}}, return_document=True
        )
        return TestResultInDB(**result) if result else None


result_repository = ResultRepository()
