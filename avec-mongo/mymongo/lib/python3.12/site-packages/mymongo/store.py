"""Mongo store."""
from typing import Any, Generic, TypeVar

from bson import ObjectId
from pydantic import BaseModel
from pymongo.collection import Collection
from querytyper import MongoQuery

from mymongo.document import Document
from mymongo.utils import utcnow

DictStrAny = dict[str, Any]
Model = TypeVar("Model", bound=BaseModel)
DatabaseModel = TypeVar("DatabaseModel", bound=Document)


class Store(Generic[Model, DatabaseModel]):
    """Mongo store."""

    def __init__(self, collection: Collection) -> None:
        """Initialize the store."""
        super().__init__()
        self.collection = collection

    @property
    def database_model(self) -> DatabaseModel:
        """Database model."""
        return self.__orig_class__.__args__[1]  # type: ignore[attr-defined]

    def read(self, document_id: ObjectId) -> DatabaseModel:
        """Read a document."""
        return self.database_model.parse_obj(self.collection.find_one({"_id": document_id}))

    def create(self, document: Model) -> DatabaseModel:
        """Create a document."""
        inserted_id = self.collection.insert_one(
            {
                **document.dict(),
                "created_at": utcnow(),
                "updated_at": utcnow(),
            }
        ).inserted_id
        return self.read(inserted_id)

    def update(self, document_id: ObjectId, document: Model) -> DatabaseModel:
        """Update a document."""
        return self.database_model.parse_obj(
            self.collection.find_one_and_update(
                {"_id": document_id},
                {
                    "$set": {
                        **document.dict(),
                        "updated_at": utcnow(),
                    }
                },
                return_document=True,
            )
        )

    def delete(
        self,
        document_id: ObjectId,
        hard: bool = False,
    ) -> None:
        """
        Delete a document.

        If hard is True, delete the document permanently.
        """
        if hard:
            self.collection.find_one_and_delete({"_id": document_id})
        else:
            self.collection.find_one_and_update(
                {"_id": document_id},
                {
                    "$set": {
                        "deleted_at": utcnow(),
                    }
                },
            )

    def find(
        self,
        query: MongoQuery | DictStrAny | None = None,
        include_deleted: bool = False,
    ) -> list[DatabaseModel]:
        """Find a document."""
        if query and not include_deleted:
            query.update({"deleted_at": None})
        return [self.database_model.parse_obj(doc) for doc in self.collection.find(query)]
