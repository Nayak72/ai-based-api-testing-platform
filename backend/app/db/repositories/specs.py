from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.models import (
    APISpecCreate,
    APISpecInDB,
    GenerationCache,
)
from app.db.mongo import get_collection


class SpecRepository:
    def __init__(self):
        self._collection: AsyncIOMotorCollection | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            self._collection = get_collection("api_specs")
        return self._collection

    async def create(self, spec: APISpecCreate, user_id: ObjectId, spec_hash: str) -> APISpecInDB:
        now = datetime.now()
        doc = {
            **spec.model_dump(),
            "user_id": user_id,
            "spec_hash": spec_hash,
            "parsed_spec": None,
            "endpoints_count": 0,
            "spec_version": None,
            "base_url": None,
            "status": "parsing",
            "parse_error": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return APISpecInDB(**doc)

    async def get_by_id(self, spec_id: ObjectId, user_id: ObjectId) -> APISpecInDB | None:
        doc = await self.collection.find_one({"_id": spec_id, "user_id": user_id})
        return APISpecInDB(**doc) if doc else None

    async def list_by_user(
        self, user_id: ObjectId, skip: int = 0, limit: int = 20, status: str | None = None
    ) -> list[APISpecInDB]:
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return [APISpecInDB(**doc) async for doc in cursor]

    async def count_by_user(self, user_id: ObjectId, status: str | None = None) -> int:
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        return await self.collection.count_documents(query)

    async def update_parsed(
        self,
        spec_id: ObjectId,
        parsed_spec: dict,
        endpoints_count: int,
        spec_version: str,
        base_url: str,
    ) -> APISpecInDB | None:
        result = await self.collection.find_one_and_update(
            {"_id": spec_id},
            {
                "$set": {
                    "parsed_spec": parsed_spec,
                    "endpoints_count": endpoints_count,
                    "spec_version": spec_version,
                    "base_url": base_url,
                    "status": "ready",
                    "parse_error": None,
                    "updated_at": datetime.now(),
                }
            },
            return_document=True,
        )
        return APISpecInDB(**result) if result else None

    async def update_status(self, spec_id: ObjectId, status: str, error: str | None = None) -> APISpecInDB | None:
        update = {"status": status, "updated_at": datetime.now()}
        if error:
            update["parse_error"] = error
        result = await self.collection.find_one_and_update({"_id": spec_id}, {"$set": update}, return_document=True)
        return APISpecInDB(**result) if result else None

    async def delete(self, spec_id: ObjectId, user_id: ObjectId) -> bool:
        result = await self.collection.delete_one({"_id": spec_id, "user_id": user_id})
        return result.deleted_count > 0


spec_repository = SpecRepository()


class TokenBlocklistRepository:
    def __init__(self):
        self._collection: AsyncIOMotorCollection | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            self._collection = get_collection("token_blocklist")
        return self._collection

    async def add(self, token_hash: str, user_id: ObjectId, expires_at: datetime) -> None:
        doc = {
            "token_hash": token_hash,
            "user_id": user_id,
            "expires_at": expires_at,
            "created_at": datetime.now(),
        }
        await self.collection.insert_one(doc)

    async def exists(self, token_hash: str) -> bool:
        doc = await self.collection.find_one({"token_hash": token_hash})
        return doc is not None


token_blocklist_repository = TokenBlocklistRepository()


class GenerationCacheRepository:
    def __init__(self):
        self._collection: AsyncIOMotorCollection | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            self._collection = get_collection("generation_cache")
        return self._collection

    async def get(
        self, spec_id: ObjectId, endpoint_id: str, category: str, prompt_version: str, model: str | None = None
    ) -> GenerationCache | None:
        query = {"spec_id": spec_id, "endpoint_id": endpoint_id, "category": category, "prompt_version": prompt_version}
        if model:
            query["model"] = model
        doc = await self.collection.find_one(query)
        return GenerationCache(**doc) if doc else None

    async def set(self, cache: GenerationCache) -> None:
        query = {
            "spec_id": cache.spec_id,
            "endpoint_id": cache.endpoint_id,
            "category": cache.category,
            "prompt_version": cache.prompt_version,
        }
        if cache.model:
            query["model"] = cache.model

        doc = cache.model_dump(by_alias=True)
        if not doc.get("_id"):
            doc["_id"] = ObjectId()

        try:
            await self.collection.replace_one(
                query,
                doc,
                upsert=True,
            )
        except Exception as e:
            if "duplicate key error" in str(e) and ("_id: null" in str(e) or "_id" in str(e)):
                await self.collection.delete_many({"_id": None})
                doc["_id"] = doc.get("_id") or ObjectId()
                await self.collection.replace_one(
                    query,
                    doc,
                    upsert=True,
                )
            else:
                raise


generation_cache_repository = GenerationCacheRepository()
