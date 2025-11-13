import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from database import db, create_document, get_documents
from schemas import (
    User, Session, NewsArticle, Announcement, GalleryItem, AdmissionInfo,
    AcademicCalendarEvent, ScheduleEntry, OrgNode, Staff, Extracurricular,
    SchoolPage, Achievement
)

app = FastAPI(title="School Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MASTER_ADMIN_EMAIL = "caproktaroy03@gmail.com"

# Utilities
class AuthResponse(BaseModel):
    token: str
    email: EmailStr


def ensure_admin(auth_token: Optional[str] = Header(None)) -> str:
    if not auth_token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    # Look up session by token
    session = db["session"].find_one({"token": auth_token, "active": True})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return session["email"]


@app.get("/")
def read_root():
    return {"message": "School Management API is running"}


# Auth endpoints (email token based, simplified)
class LoginRequest(BaseModel):
    email: EmailStr


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    email = payload.email.lower()
    # Only allow master admin for now
    if email != MASTER_ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses admin")

    # create or update user doc
    db["user"].update_one(
        {"email": email},
        {"$set": {"email": email, "name": "Admin Master", "role": "admin", "updated_at": datetime.now(timezone.utc)},
         "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True
    )

    # create a simple token and session
    token = os.urandom(24).hex()
    db["session"].insert_one({
        "email": email,
        "token": token,
        "active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })
    return {"token": token, "email": email}


@app.post("/auth/logout")
def logout(auth_token: Optional[str] = Header(None)):
    if not auth_token:
        return {"message": "ok"}
    db["session"].update_one({"token": auth_token}, {"$set": {"active": False, "updated_at": datetime.now(timezone.utc)}})
    return {"message": "logged out"}


# Generic CRUD helpers
class Document(BaseModel):
    data: Dict[str, Any]


def create_item(collection: str, data: Dict[str, Any]):
    # Validate with Pydantic by mapping collection to schema
    schema_map = {
        "newsarticle": NewsArticle,
        "announcement": Announcement,
        "galleryitem": GalleryItem,
        "admissioninfo": AdmissionInfo,
        "academiccalendarevent": AcademicCalendarEvent,
        "scheduleentry": ScheduleEntry,
        "orgnode": OrgNode,
        "staff": Staff,
        "extracurricular": Extracurricular,
        "schoolpage": SchoolPage,
        "achievement": Achievement,
    }
    Model = schema_map.get(collection)
    if not Model:
        raise HTTPException(status_code=400, detail="Unknown collection")
    model = Model(**data)
    doc = model.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = datetime.now(timezone.utc)
    result = db[collection].insert_one(doc)
    return {"_id": str(result.inserted_id)}


from bson import ObjectId

def obj_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


@app.get("/public/{collection}")
def public_list(collection: str, limit: int = 50):
    # public fetch without auth for frontend display
    items = list(db[collection].find({}).sort("created_at", -1).limit(limit))
    for it in items:
        it["_id"] = str(it["_id"])
    return items


@app.get("/admin/{collection}")
def admin_list(collection: str, email: str = Depends(ensure_admin), limit: int = 200):
    items = list(db[collection].find({}).sort("created_at", -1).limit(limit))
    for it in items:
        it["_id"] = str(it["_id"])
    return items


@app.post("/admin/{collection}")
def admin_create(collection: str, payload: Document, email: str = Depends(ensure_admin)):
    return create_item(collection, payload.data)


@app.put("/admin/{collection}/{item_id}")
def admin_update(collection: str, item_id: str, payload: Document, email: str = Depends(ensure_admin)):
    data = payload.data
    data["updated_at"] = datetime.now(timezone.utc)
    result = db[collection].update_one({"_id": obj_id(item_id)}, {"$set": data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "updated"}


@app.delete("/admin/{collection}/{item_id}")
def admin_delete(collection: str, item_id: str, email: str = Depends(ensure_admin)):
    result = db[collection].delete_one({"_id": obj_id(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "deleted"}


# Convenience routes for profile pages keys to ensure single doc per key
@app.get("/public/page/{key}")
def get_page(key: str):
    doc = db["schoolpage"].find_one({"key": key})
    if not doc:
        return {"key": key, "title": "", "content": ""}
    doc["_id"] = str(doc["_id"])
    return doc


@app.post("/admin/page/{key}")
def set_page(key: str, payload: Document, email: str = Depends(ensure_admin)):
    data = payload.data
    data["key"] = key
    data["updated_at"] = datetime.now(timezone.utc)
    db["schoolpage"].update_one({"key": key}, {"$set": data, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"message": "saved"}


# Health and database test
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:20]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
