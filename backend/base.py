"""floks-pc DCA Orchestrator — MongoDB + Pydantic base document.

Maps _id (ObjectId) → id (str). Never returns raw Mongo docs.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Annotated, Any, Optional
from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _validate_oid(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and (v == "" or ObjectId.is_valid(v)):
        return v
    raise ValueError(f"Invalid ObjectId: {v!r}")


PyObjectId = Annotated[str, BeforeValidator(_validate_oid)]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None)
    created_at: str = Field(default_factory=utcnow_iso)

    @classmethod
    def from_mongo(cls, doc: dict | None):
        if not doc:
            return None
        doc = dict(doc)
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return cls(**doc)

    def to_mongo(self) -> dict:
        d = self.model_dump(exclude_none=True)
        if "id" in d and d["id"]:
            try:
                d["_id"] = ObjectId(d.pop("id"))
            except Exception:
                d.pop("id")
        else:
            d.pop("id", None)
        return d
