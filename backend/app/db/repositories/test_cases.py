
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.models import TestCaseCreate, TestCaseInDB
from app.db.mongo import get_collection


class TestCaseRepository:
    def __init__(self):
        self._collection: AsyncIOMotorCollection | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            self._collection = get_collection("test_cases")
        return self._collection

    async def upsert(self, test_case: TestCaseCreate) -> TestCaseInDB:
        doc = test_case.model_dump(by_alias=True)
        request_hash = doc["metadata"]["request_hash"]
        filter_query = {
            "spec_id": doc["spec_id"],
            "endpoint_id": doc["endpoint_id"],
            "category": doc["category"],
            "subcategory": doc["subcategory"],
            "metadata.request_hash": request_hash,
        }
        result = await self.collection.find_one_and_update(
            filter_query,
            {"$set": doc, "$setOnInsert": {"created_at": doc.get("created_at")}},
            upsert=True,
            return_document=True,
        )
        return TestCaseInDB(**result)

    async def bulk_upsert(self, test_cases: list[TestCaseCreate]) -> int:
        if not test_cases:
            return 0
        from pymongo import UpdateOne

        operations = []
        for tc in test_cases:
            doc = tc.model_dump(by_alias=True)
            request_hash = doc["metadata"]["request_hash"]
            filter_query = {
                "spec_id": doc["spec_id"],
                "endpoint_id": doc["endpoint_id"],
                "category": doc["category"],
                "subcategory": doc["subcategory"],
                "metadata.request_hash": request_hash,
            }
            operations.append(
                UpdateOne(
                    filter_query,
                    {"$set": doc, "$setOnInsert": {"created_at": doc.get("created_at")}},
                    upsert=True,
                )
            )
        result = await self.collection.bulk_write(operations)
        return result.upserted_count + result.modified_count

    async def get_by_id(self, test_case_id: ObjectId) -> TestCaseInDB | None:
        doc = await self.collection.find_one({"_id": test_case_id})
        return TestCaseInDB(**doc) if doc else None

    async def list_by_spec(
        self,
        spec_id: ObjectId,
        endpoint_id: str | None = None,
        category: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TestCaseInDB]:
        query = {"spec_id": spec_id}
        if endpoint_id:
            query["endpoint_id"] = endpoint_id
        if category:
            query["category"] = category
        cursor = self.collection.find(query).sort("created_at", 1).skip(skip).limit(limit)
        return [TestCaseInDB(**doc) async for doc in cursor]

    async def count_by_spec(self, spec_id: ObjectId, endpoint_id: str | None = None, category: str | None = None) -> int:
        query = {"spec_id": spec_id}
        if endpoint_id:
            query["endpoint_id"] = endpoint_id
        if category:
            query["category"] = category
        return await self.collection.count_documents(query)

    async def delete(self, test_case_id: ObjectId) -> bool:
        result = await self.collection.delete_one({"_id": test_case_id})
        return result.deleted_count > 0

    async def delete_by_spec(self, spec_id: ObjectId) -> int:
        result = await self.collection.delete_many({"spec_id": spec_id})
        return result.deleted_count


test_case_repository = TestCaseRepository()
