#!/usr/bin/env python
"""
MongoDB helper module for webscraper-agent.
Provides functionality to connect to MongoDB and perform operations on the lowcygier database.
"""

import os
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class MongoDBHelper:
    """Helper class for MongoDB operations."""

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize MongoDB helper.

        Args:
            connection_string: MongoDB connection URI string. If None, uses MONGO_URI env var.
        """
        self.connection_string = connection_string or os.environ.get(
            "MONGO_URI", "mongodb://localhost:27017/"
        )
        self.client = None
        self.db = None

    def connect(self, db_name: str = "lowcy_gier") -> Optional[Database]:
        """
        Connect to MongoDB and return database object.

        Args:
            db_name: Name of the database to connect to. Defaults to "lowcy_gier".

        Returns:
            Database object or None if connection failed
        """
        try:
            self.client = MongoClient(self.connection_string)
            # Check connection by issuing a simple command
            self.client.admin.command("ping")
            self.db = self.client[db_name]
            return self.db
        except ConnectionFailure as e:
            print(f"MongoDB connection failed: {e}")
            return None

    def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()

    def get_collection(self, collection_name: str = "data") -> Optional[Collection]:
        """
        Get collection from connected database.

        Args:
            collection_name: Name of the collection to get. Defaults to "data".

        Returns:
            Collection object or None if not connected
        """
        if self.db:
            return self.db[collection_name]
        return None

    def insert_one(self, collection_name: str, document: Dict[str, Any]) -> None:
        """
        Insert a single document into a collection.

        Args:
            collection_name: Name of the collection to insert the document into.
            document: The document to insert.
        """
        collection = self.get_collection(collection_name)
        collection.insert_one(document)

    def find(self, collection_name: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find documents in a collection that match a query.

        Args:
            collection_name: Name of the collection to search.
            query: The query to match documents against.

        Returns:
            List[Dict[str, Any]]: List of matching documents.
        """
        collection = self.get_collection(collection_name)
        return list(collection.find(query))

    def update_one(
        self, collection_name: str, query: Dict[str, Any], update: Dict[str, Any]
    ) -> None:
        """
        Update a single document in a collection.

        Args:
            collection_name: Name of the collection to update the document in.
            query: The query to match the document to update.
            update: The update to apply to the matched document.
        """
        collection = self.get_collection(collection_name)
        collection.update_one(query, {"$set": update})

    def delete_one(self, collection_name: str, query: Dict[str, Any]) -> None:
        """
        Delete a single document from a collection.

        Args:
            collection_name: Name of the collection to delete the document from.
            query: The query to match the document to delete.
        """
        collection = self.get_collection(collection_name)
        collection.delete_one(query)

    def save_news_items(
        self, news_items: List[Dict[str, Any]], collection_name: str = "data"
    ) -> int:
        """
        Save news items to MongoDB with unique constraint on URL.

        Args:
            news_items: List of news items to save
            collection_name: Name of the collection to save to. Defaults to "data".

        Returns:
            Number of items inserted
        """
        if self.db is None:
            print("No database connection.")
            return 0

        collection = self.db[collection_name]

        # Add timestamp for when the items were added to DB
        for item in news_items:
            item["stored_at"] = datetime.now().isoformat()

        # Create a unique index on URL if it doesn't exist
        collection.create_index("url", unique=True)

        # Insert items, skipping duplicates
        insert_count = 0
        for item in news_items:
            try:
                # upsert=True will update if exists, insert if not
                result = collection.update_one(
                    {"url": item["url"]}, {"$set": item}, upsert=True
                )
                if result.upserted_id:
                    insert_count += 1
            except Exception as e:
                print(f"Error saving item: {e}")

        return insert_count

    def find_news_items(
        self,
        query: Dict[str, Any] = None,
        limit: int = 0,
        sort_by: List[tuple] = None,
        collection_name: str = "data",
    ) -> List[Dict[str, Any]]:
        """
        Find news items in MongoDB.

        Args:
            query: MongoDB query dictionary
            limit: Maximum number of items to return (0 for all)
            sort_by: List of (field, direction) tuples to sort by
            collection_name: Name of the collection to query. Defaults to "data".

        Returns:
            List of news items matching the query
        """
        if not self.db:
            return []

        collection = self.db[collection_name]

        # Default query is empty to match all documents
        if query is None:
            query = {}

        cursor = collection.find(query)

        # Apply limit if specified
        if limit > 0:
            cursor = cursor.limit(limit)

        # Apply sort if specified
        if sort_by:
            cursor = cursor.sort(sort_by)

        # Convert cursor to list before returning
        return list(cursor)

    def count_news_items(
        self, query: Dict[str, Any] = None, collection_name: str = "data"
    ) -> int:
        """
        Count news items in MongoDB.

        Args:
            query: MongoDB query dictionary
            collection_name: Name of the collection to query. Defaults to "data".

        Returns:
            Number of items matching the query
        """
        if not self.db:
            return 0

        collection = self.db[collection_name]

        # Default query is empty to match all documents
        if query is None:
            query = {}

        return collection.count_documents(query)
