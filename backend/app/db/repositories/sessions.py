"""Session repository for agentic test sessions."""

from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_collection


class SessionRepository:
    def __init__(self) -> None:
        self._collection: AsyncIOMotorCollection | None = None
        self._events_collection: AsyncIOMotorCollection | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            self._collection = get_collection("sessions")
        return self._collection

    @property
    def events_collection(self) -> AsyncIOMotorCollection:
        if self._events_collection is None:
            self._events_collection = get_collection("agent_events")
        return self._events_collection

    async def create(self, user_id: ObjectId, data: dict) -> dict:
        now = datetime.now()
        doc = {
            **data,
            "user_id": user_id,
            "status": "started",
            "created_at": now,
            "updated_at": now,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def get_by_id(self, session_id: ObjectId, user_id: ObjectId) -> dict | None:
        return await self.collection.find_one({"_id": session_id, "user_id": user_id})

    async def list_by_user(self, user_id: ObjectId, limit: int = 20) -> list[dict]:
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        return [doc async for doc in cursor]

    async def update(self, session_id: ObjectId, update: dict) -> None:
        update["updated_at"] = datetime.now()
        await self.collection.update_one({"_id": session_id}, {"$set": update})

    async def get_events(self, session_id: str, after_ts: str | None = None) -> list[dict]:
        """Retrieve persisted agent events for a session (for SSE replay)."""
        query: dict = {"session_id": session_id}
        if after_ts:
            query["ts"] = {"$gt": after_ts}
        cursor = self.events_collection.find(query).sort("ts", 1).limit(500)
        return [doc async for doc in cursor]


session_repository = SessionRepository()
