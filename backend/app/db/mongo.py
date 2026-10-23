import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

logger = structlog.get_logger()

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    global _client, _db
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _db = _client[settings.mongodb_db]
    logger.info("Connected to MongoDB", db=settings.mongodb_db)


async def close_mongo_connection() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("Closed MongoDB connection")


def get_database() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo first.")
    return _db


def get_collection(name: str):
    return get_database()[name]


async def create_indexes() -> None:
    db = get_database()

    # users
    await db.users.create_index("email", unique=True)
    await db.users.create_index([("is_active", 1), ("created_at", -1)])

    # token_blocklist
    await db.token_blocklist.create_index("expires_at", expireAfterSeconds=0)
    await db.token_blocklist.create_index("user_id")

    # api_specs
    await db.api_specs.create_index([("user_id", 1), ("created_at", -1)])
    await db.api_specs.create_index("status")
    await db.api_specs.create_index("spec_hash")
    await db.api_specs.create_index("created_at", expireAfterSeconds=7776000)  # 90 days optional

    # generation_cache
    await db.generation_cache.create_index(
        [("spec_id", 1), ("endpoint_id", 1), ("category", 1), ("prompt_version", 1)],
        unique=True,
    )
    await db.generation_cache.create_index("prompt_hash")

    # test_cases
    await db.test_cases.create_index([("spec_id", 1), ("endpoint_id", 1), ("category", 1)])
    await db.test_cases.create_index("category")
    await db.test_cases.create_index("metadata.severity")
    await db.test_cases.create_index(
        [("spec_id", 1), ("endpoint_id", 1), ("category", 1), ("subcategory", 1), ("metadata.request_hash", 1)],
        unique=True,
    )

    # test_runs
    await db.test_runs.create_index([("user_id", 1), ("created_at", -1)])
    await db.test_runs.create_index([("spec_id", 1), ("created_at", -1)])
    await db.test_runs.create_index("status")

    # test_results
    await db.test_results.create_index([("run_id", 1), ("endpoint_id", 1), ("category", 1)])
    await db.test_results.create_index([("run_id", 1), ("status", 1)])
    await db.test_results.create_index("test_case_id")

    # reports
    await db.reports.create_index("run_id", unique=True)
    await db.reports.create_index([("user_id", 1), ("generated_at", -1)])

    logger.info("All indexes created")
