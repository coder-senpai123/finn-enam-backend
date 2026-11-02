import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import motor.motor_asyncio
from app.config import Settings

_mongo_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_db = None
_is_connected: bool = False

# Resilient in-memory fallback store
_MEM_USERS: Dict[str, Dict[str, Any]] = {}

async def init_mongodb() -> bool:
    """
    Initializes connection to MongoDB using MONGODB_URL from environment.
    """
    global _mongo_client, _db, _is_connected
    # Always read fresh settings from .env
    settings = Settings()
    if not settings.MONGODB_URL:
        _is_connected = False
        return False

    try:
        # Use 5 second timeout for remote MongoDB Atlas connections
        client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000
        )
        # Verify connection
        await client.admin.command('ping')
        _mongo_client = client
        _db = _mongo_client[settings.MONGODB_DB_NAME]
        _is_connected = True
        print(f"[OK] MongoDB Atlas successfully connected to database: {settings.MONGODB_DB_NAME}")
        return True
    except Exception as e:
        _is_connected = False
        print(f"[INFO] MongoDB connection notice ({type(e).__name__}): {e}")
        return False

def is_mongodb_live() -> bool:
    global _is_connected
    return _is_connected

async def get_db_collection(collection_name: str):
    global _db, _is_connected
    if not _is_connected or _db is None:
        await init_mongodb()
    if _is_connected and _db is not None:
        return _db[collection_name]
    return None

async def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    clean_email = email.lower().strip()
    coll = await get_db_collection("users")
    if coll is not None:
        try:
            doc = await coll.find_one({"email": clean_email})
            if doc:
                doc["_id"] = str(doc.get("_id", clean_email))
                return doc
        except Exception as e:
            print(f"MongoDB read error: {e}")

    # Fallback in-memory
    return _MEM_USERS.get(clean_email)

async def upsert_user(email: str, update_fields: Dict[str, Any]) -> Dict[str, Any]:
    clean_email = email.lower().strip()
    now_iso = datetime.utcnow().isoformat()
    update_fields["updated_at"] = now_iso

    # Update in-memory
    existing = _MEM_USERS.get(clean_email, {"email": clean_email, "created_at": now_iso})
    existing.update(update_fields)
    _MEM_USERS[clean_email] = existing

    # Upsert in MongoDB
    coll = await get_db_collection("users")
    if coll is not None:
        try:
            await coll.update_one(
                {"email": clean_email},
                {"$set": update_fields, "$setOnInsert": {"email": clean_email, "created_at": now_iso}},
                upsert=True
            )
        except Exception as e:
            print(f"MongoDB upsert error: {e}")

    return existing
