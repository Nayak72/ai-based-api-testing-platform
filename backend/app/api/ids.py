"""Shared validation for externally supplied MongoDB identifiers."""

from bson import ObjectId
from fastapi import HTTPException, status


def parse_object_id(value: str, resource: str = "resource") -> ObjectId:
    """Return a valid ObjectId or a stable client-facing validation error."""
    if not ObjectId.is_valid(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {resource} ID",
        )
    return ObjectId(value)
