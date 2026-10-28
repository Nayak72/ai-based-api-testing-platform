from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.models import ProviderProfileCreate, ProviderProfileInDB, ProviderProfileUpdate
from app.db.mongo import get_collection
from app.safety.secrets import decrypt_secret, encrypt_secret


class ProviderRepository:
    def __init__(self):
        self._collection: AsyncIOMotorCollection | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            self._collection = get_collection("provider_profiles")
        return self._collection

    async def create(self, profile: ProviderProfileCreate, user_id: ObjectId) -> ProviderProfileInDB:
        now = datetime.now()
        api_key_encrypted = encrypt_secret(profile.api_key) if profile.api_key else None
        doc = {
            **profile.model_dump(exclude={"api_key"}),
            "user_id": user_id,
            "api_key_encrypted": api_key_encrypted,
            "has_key": bool(api_key_encrypted),
            "created_at": now,
            "updated_at": now,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return ProviderProfileInDB(**doc)

    async def get_by_id(self, profile_id: ObjectId, user_id: ObjectId) -> ProviderProfileInDB | None:
        doc = await self.collection.find_one({"_id": profile_id, "user_id": user_id})
        if doc:
            return ProviderProfileInDB(**doc)
        return None

    async def list_by_user(self, user_id: ObjectId) -> list[ProviderProfileInDB]:
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1)
        profiles = []
        async for doc in cursor:
            profile = ProviderProfileInDB(**doc)
            profiles.append(profile)
        return profiles

    async def update(
        self, profile_id: ObjectId, user_id: ObjectId, update: ProviderProfileUpdate
    ) -> ProviderProfileInDB | None:
        update_data = update.model_dump(exclude_unset=True, exclude={"api_key"})
        if update.api_key is not None:
            update_data["api_key_encrypted"] = encrypt_secret(update.api_key) if update.api_key else None
            update_data["has_key"] = bool(update_data.get("api_key_encrypted"))
        update_data["updated_at"] = datetime.now()

        result = await self.collection.find_one_and_update(
            {"_id": profile_id, "user_id": user_id},
            {"$set": update_data},
            return_document=True,
        )
        return ProviderProfileInDB(**result) if result else None

    async def delete(self, profile_id: ObjectId, user_id: ObjectId) -> bool:
        result = await self.collection.delete_one({"_id": profile_id, "user_id": user_id})
        return result.deleted_count > 0

    async def get_default(self, user_id: ObjectId, preset: str | None = None) -> ProviderProfileInDB | None:
        query = {"user_id": user_id, "is_default": True}
        if preset:
            query["preset"] = preset
        doc = await self.collection.find_one(query)
        return ProviderProfileInDB(**doc) if doc else None

    async def set_default(self, profile_id: ObjectId, user_id: ObjectId) -> None:
        await self.collection.update_many(
            {"user_id": user_id, "is_default": True},
            {"$set": {"is_default": False}},
        )
        await self.collection.update_one(
            {"_id": profile_id, "user_id": user_id},
            {"$set": {"is_default": True}},
        )

    def get_decrypted_key(self, profile: ProviderProfileInDB) -> str | None:
        if profile.api_key_encrypted:
            return decrypt_secret(profile.api_key_encrypted)
        return None


provider_repository = ProviderRepository()
