from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId
from pydantic_core import core_schema
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from typing import Any


class PyObjectId(ObjectId):
    """Custom ObjectId compatible with Pydantic v2."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler: GetCoreSchemaHandler):
        # ✅ Accept both ObjectId and string representations
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.no_info_after_validator_function(cls.validate, core_schema.str_schema())
        ])

    @classmethod
    def validate(cls, v: Any) -> ObjectId:
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler: GetJsonSchemaHandler):
        json_schema = handler(core_schema)
        json_schema.update(type="string", examples=["60c5baaf2f8e4c23d8f72c90"])
        return json_schema

class UserModel(BaseModel):
    """User database model"""

    id: Optional[PyObjectId] = Field(
        default=None,
        validation_alias="_id",  # ✅ this fixes the ObjectId -> str issue
        serialization_alias="_id"
    )
    email: EmailStr
    name: str
    hashed_password: str
    role: str = "job_seeker"
    is_active: bool = True
    email_verified: bool = False
    profile: Optional[dict] = None
    subscription: Optional[dict] = {
        "plan": "free",
        "interviews_remaining": 3,
        "expires_at": None
    }
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "role": "job_seeker",
                "is_active": True,
                "email_verified": False
            }
        }
