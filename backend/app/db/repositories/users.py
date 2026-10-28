from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.core.security import hash_password, hash_refresh_token
from app.db.models import UserCreate, UserInDB, UserUpdate
from app.db.mongo import get_collection


class UserRepository:
    def __init__(self):
        self._collection: AsyncIOMotorCollection | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            self._collection = get_collection("users")
        return self._collection

    async def create(self, user: UserCreate) -> UserInDB:
        now = datetime.now()
        doc = {
            "email": user.email,
            "full_name": user.full_name,
            "password_hash": hash_password(user.password),
            "is_active": True,
            "is_superuser": False,
            "created_at": now,
            "updated_at": now,
            "last_login": None,
            "refresh_tokens": [],
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return UserInDB(**doc)

    async def get_by_id(self, user_id: ObjectId) -> UserInDB | None:
        doc = await self.collection.find_one({"_id": user_id})
        return UserInDB(**doc) if doc else None

    async def get_by_email(self, email: str) -> UserInDB | None:
        doc = await self.collection.find_one({"email": email})
        return UserInDB(**doc) if doc else None

    async def update(self, user_id: ObjectId, update: UserUpdate) -> UserInDB | None:
        update_data = {"updated_at": datetime.now()}
        if update.full_name is not None:
            update_data["full_name"] = update.full_name
        if update.password is not None:
            update_data["password_hash"] = hash_password(update.password)

        result = await self.collection.find_one_and_update(
            {"_id": user_id},
            {"$set": update_data},
            return_document=True,
        )
        return UserInDB(**result) if result else None

    async def update_last_login(self, user_id: ObjectId) -> None:
        await self.collection.update_one(
            {"_id": user_id},
            {"$set": {"last_login": datetime.now()}},
        )

    async def add_refresh_token(self, user_id: ObjectId, token: str, max_tokens: int = 5) -> None:
        token_hash = hash_refresh_token(token)
        await self.collection.update_one(
            {"_id": user_id},
            {
                "$push": {"refresh_tokens": {"$each": [token_hash], "$slice": -max_tokens}},
                "$set": {"updated_at": datetime.now()},
            },
        )

    async def remove_refresh_token(self, user_id: ObjectId, token: str) -> None:
        token_hash = hash_refresh_token(token)
        await self.collection.update_one(
            {"_id": user_id},
            {"$pull": {"refresh_tokens": token_hash}, "$set": {"updated_at": datetime.now()}},
        )

    async def clear_refresh_tokens(self, user_id: ObjectId) -> None:
        await self.collection.update_one(
            {"_id": user_id},
            {"$set": {"refresh_tokens": [], "updated_at": datetime.now()}},
        )

    async def verify_refresh_token(self, user_id: ObjectId, token: str) -> bool:
        token_hash = hash_refresh_token(token)
        doc = await self.collection.find_one({"_id": user_id, "refresh_tokens": token_hash})
        return doc is not None


user_repository = UserRepository()
