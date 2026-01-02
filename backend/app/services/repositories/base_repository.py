"""
Base Repository Pattern for MongoDB Operations
Provides generic CRUD operations with type safety
"""
from typing import Optional, List, Dict, Any, TypeVar, Generic
from bson import ObjectId
from pymongo.collection import Collection
from pymongo import ReturnDocument
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Generic repository for MongoDB collections
    Handles common CRUD operations with proper error handling
    """

    def __init__(self, collection: Collection, model_class: type):
        """
        Initialize repository with MongoDB collection and Pydantic model
        
        Args:
            collection: MongoDB collection instance
            model_class: Pydantic model class for validation
        """
        self.collection = collection
        self.model_class = model_class

    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Find document by ID
        
        Args:
            id: Document ID as string
            
        Returns:
            Document dict or None if not found
        """
        try:
            return await self.collection.find_one({"_id": ObjectId(id)})
        except Exception as e:
            logger.error(f"Error finding document by ID {id}: {e}")
            return None

    async def find_one(self, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find single document by filter
        
        Args:
            filter: MongoDB filter dict
            
        Returns:
            Document dict or None
        """
        try:
            return await self.collection.find_one(filter)
        except Exception as e:
            logger.error(f"Error finding document with filter {filter}: {e}")
            return None

    async def find_many(
        self, 
        filter: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 100,
        sort: Optional[List[tuple]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents
        
        Args:
            filter: MongoDB filter dict
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort: List of (field, direction) tuples for sorting
            
        Returns:
            List of document dicts
        """
        try:
            cursor = self.collection.find(filter).skip(skip).limit(limit)
            
            if sort:
                cursor = cursor.sort(sort)
                
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error finding documents with filter {filter}: {e}")
            return []

    async def create(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Create new document
        
        Args:
            data: Document data (without _id)
            
        Returns:
            Inserted document ID as string, or None on failure
        """
        try:
            # Add timestamps
            data["created_at"] = datetime.utcnow()
            data["updated_at"] = datetime.utcnow()
            
            result = await self.collection.insert_one(data)
            logger.info(f"Created document with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            return None

    async def update(
        self, 
        id: str, 
        update_data: Dict[str, Any],
        return_document: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Update document by ID
        
        Args:
            id: Document ID as string
            update_data: Fields to update (use $set, $push, etc.)
            return_document: If True, return updated document
            
        Returns:
            Updated document if return_document=True, else None
        """
        try:
            # Always update the updated_at timestamp
            if "$set" in update_data:
                update_data["$set"]["updated_at"] = datetime.utcnow()
            else:
                update_data["$set"] = {"updated_at": datetime.utcnow()}
            
            if return_document:
                result = await self.collection.find_one_and_update(
                    {"_id": ObjectId(id)},
                    update_data,
                    return_document=ReturnDocument.AFTER
                )
                return result
            else:
                await self.collection.update_one(
                    {"_id": ObjectId(id)},
                    update_data
                )
                return None
        except Exception as e:
            logger.error(f"Error updating document {id}: {e}")
            return None

    async def update_many(
        self, 
        filter: Dict[str, Any], 
        update_data: Dict[str, Any]
    ) -> int:
        """
        Update multiple documents
        
        Args:
            filter: MongoDB filter dict
            update_data: Update operations
            
        Returns:
            Number of documents modified
        """
        try:
            if "$set" in update_data:
                update_data["$set"]["updated_at"] = datetime.utcnow()
            else:
                update_data["$set"] = {"updated_at": datetime.utcnow()}
                
            result = await self.collection.update_many(filter, update_data)
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating documents with filter {filter}: {e}")
            return 0

    async def delete(self, id: str) -> bool:
        """
        Delete document by ID
        
        Args:
            id: Document ID as string
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.collection.delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting document {id}: {e}")
            return False

    async def count(self, filter: Dict[str, Any] = None) -> int:
        """
        Count documents matching filter
        
        Args:
            filter: MongoDB filter dict (None for all documents)
            
        Returns:
            Number of matching documents
        """
        try:
            if filter is None:
                filter = {}
            return await self.collection.count_documents(filter)
        except Exception as e:
            logger.error(f"Error counting documents: {e}")
            return 0

    async def exists(self, id: str) -> bool:
        """
        Check if document exists by ID
        
        Args:
            id: Document ID as string
            
        Returns:
            True if exists, False otherwise
        """
        try:
            count = await self.collection.count_documents(
                {"_id": ObjectId(id)}, 
                limit=1
            )
            return count > 0
        except Exception as e:
            logger.error(f"Error checking existence of document {id}: {e}")
            return False