from datetime import UTC, datetime

from bson import ObjectId

from app.db.mongo import get_collection


class GenerationUnitRepository:
    @property
    def collection(self):
        return get_collection("generation_units")

    async def ensure(self, *, session_id: str, spec_id: ObjectId, endpoint_id: str, category: str, subcategory: str) -> dict:
        now = datetime.now(UTC)
        await self.collection.update_one(
            {
                "session_id": session_id,
                "endpoint_id": endpoint_id,
                "category": category,
                "subcategory": subcategory,
            },
            {
                "$setOnInsert": {
                    "session_id": session_id,
                    "spec_id": spec_id,
                    "endpoint_id": endpoint_id,
                    "category": category,
                    "subcategory": subcategory,
                    "status": "pending",
                    "attempts": 0,
                    "error_code": None,
                    "error": None,
                    "tokens": 0,
                    "test_case_ids": [],
                    "created_at": now,
                }
            },
            upsert=True,
        )
        return await self.collection.find_one({
            "session_id": session_id,
            "endpoint_id": endpoint_id,
            "category": category,
            "subcategory": subcategory,
        })

    async def start(self, unit_id: ObjectId) -> None:
        await self.collection.update_one(
            {"_id": unit_id},
            {"$set": {"status": "running", "started_at": datetime.now(UTC), "error": None, "error_code": None}, "$inc": {"attempts": 1}},
        )

    async def finish(
        self,
        unit_id: ObjectId,
        *,
        status: str,
        error_code: str | None = None,
        error: str | None = None,
        tokens: int = 0,
        test_case_ids: list[str] | None = None,
    ) -> None:
        fields = {
            "status": status,
            "finished_at": datetime.now(UTC),
            "error_code": error_code,
            "error": error,
            "tokens": tokens,
        }
        if test_case_ids is not None:
            fields["test_case_ids"] = test_case_ids
        await self.collection.update_one({"_id": unit_id}, {"$set": fields})

    async def list_for_session(self, session_id: str) -> list[dict]:
        return await self.collection.find({"session_id": session_id}).sort("created_at", 1).to_list(length=10000)


generation_unit_repository = GenerationUnitRepository()
