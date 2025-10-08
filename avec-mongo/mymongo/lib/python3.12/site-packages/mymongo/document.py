"""Document model."""
from datetime import datetime

import bson
from pydantic import BaseModel, Field

ID = "_id"


class DocumentNotFoundError(Exception):
    """Document not found error."""


class Document(BaseModel):
    """A class representing a document in MongoDB."""

    class Config:
        """Model configuration."""

        arbitrary_types_allowed = True

    id: bson.ObjectId = Field(
        alias=ID,
        description="The document unique identifier in MongoDB.",
    )
    created_at: datetime = Field(
        description="The datetime when the document was created in MongoDB.",
    )
    updated_at: datetime = Field(
        description="The datetime when the document was updated in MongoDB last time.",
    )
    deleted_at: None | datetime = Field(
        default=None,
        description="The datetime when the document was deleted in MongoDB.",
    )
