from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.models import ReportBase, ReportInDB
from app.db.mongo import get_collection


class ReportRepository:
    def __init__(self):
        self._collection: AsyncIOMotorCollection | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            self._collection = get_collection("reports")
        return self._collection

    async def create(self, report: ReportBase, html_path: str | None = None, pdf_path: str | None = None) -> ReportInDB:
        now = datetime.now()
        doc = {
            **report.model_dump(),
            "html_path": html_path,
            "pdf_path": pdf_path,
            "generated_at": now,
            "file_size_bytes": 0,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return ReportInDB(**doc)

    async def get_by_id(self, report_id: ObjectId) -> ReportInDB | None:
        doc = await self.collection.find_one({"_id": report_id})
        return ReportInDB(**doc) if doc else None

    async def get_by_run(self, run_id: ObjectId) -> ReportInDB | None:
        doc = await self.collection.find_one({"run_id": run_id})
        return ReportInDB(**doc) if doc else None

    async def list_by_user(self, user_id: ObjectId, skip: int = 0, limit: int = 20) -> list[ReportInDB]:
        cursor = self.collection.find({"user_id": user_id}).sort("generated_at", -1).skip(skip).limit(limit)
        return [ReportInDB(**doc) async for doc in cursor]

    async def update_file_info(
        self, report_id: ObjectId, html_path: str | None = None, pdf_path: str | None = None, size: int = 0
    ) -> ReportInDB | None:
        update = {}
        if html_path:
            update["html_path"] = html_path
        if pdf_path:
            update["pdf_path"] = pdf_path
        if size:
            update["file_size_bytes"] = size
        result = await self.collection.find_one_and_update({"_id": report_id}, {"$set": update}, return_document=True)
        return ReportInDB(**result) if result else None


report_repository = ReportRepository()
