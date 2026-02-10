"""MongoDB utility functions for MindVault.

This module provides functions for MongoDB connections and data operations.
"""

from typing import Dict, List, Any
from pymongo import MongoClient
from pymongo.database import Database
from mindvault.core.config import settings
from mindvault.core.logger_setup import get_logger

logger = get_logger(__name__)

def get_mongo_client() -> MongoClient:
    """Establish and return a MongoDB client connection.

    Returns:
        A MongoDB client instance
    """
    try:
        client = MongoClient(settings.mongodb_uri)
        # Test connection with a ping
        client.admin.command('ping')
        logger.debug("MongoDB connection established successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise ConnectionError(f"Failed to connect to MongoDB: {e}")

def get_mongo_db() -> Database:
    """Get the MongoDB database instance.

    Returns:
        MongoDB database instance
    """
    client = get_mongo_client()
    return client[settings.db_name]

def save_raw_tweet(tweet_id: str, data: Dict[str, Any]) -> str:
    """Save raw tweet data to MongoDB.

    Args:
        tweet_id: Twitter ID to use as document ID
        data: Raw tweet data (dictionary)

    Returns:
        The ID of the inserted/updated document
    """
    try:
        db = get_mongo_db()
        result = db[settings.raw_data_collection].update_one(
            {"_id": tweet_id},
            {"$set": data},
            upsert=True
        )
        action = "Updated" if result.modified_count > 0 else "Inserted"
        logger.debug(f"{action} raw tweet data for ID {tweet_id}")
        return tweet_id
    except Exception as e:
        logger.error(f"Error saving raw tweet {tweet_id} to MongoDB: {e}")
        raise

def save_extracted_tweet(tweet_id: str, data: Dict[str, Any]) -> str:
    """Save extracted tweet data to MongoDB.

    Args:
        tweet_id: Twitter ID to use as document ID
        data: Extracted tweet data (dictionary from Pydantic model dump)

    Returns:
        The ID of the inserted/updated document
    """
    try:
        db = get_mongo_db()
        result = db[settings.extracted_data_collection].update_one(
            {"_id": tweet_id},
            {"$set": data},
            upsert=True
        )
        action = "Updated" if result.modified_count > 0 else "Inserted"
        logger.debug(f"{action} extracted tweet data for ID {tweet_id}")
        return tweet_id
    except Exception as e:
        logger.error(f"Error saving extracted tweet {tweet_id} to MongoDB: {e}")
        raise

def get_extracted_media_for_tweets(tweet_ids: List[str]) -> List[Dict[str, Any]]:
    """Get extracted media for a list of tweet IDs.

    Args:
        tweet_ids: List of tweet IDs to get media for

    Returns:
        List of extracted media items from the specified tweets
    """
    try:
        db = get_mongo_db()
        extracted_tweets = db[settings.extracted_data_collection].find(
            {"_id": {"$in": tweet_ids}}
        )
        
        all_media = []
        for tweet in extracted_tweets:
            # Add media from main tweet
            if "main_tweet" in tweet and "extracted_media" in tweet["main_tweet"]:
                all_media.extend(tweet["main_tweet"]["extracted_media"])
            
            # Add media from replies
            if "replies" in tweet:
                for reply in tweet["replies"]:
                    if "extracted_media" in reply:
                        all_media.extend(reply["extracted_media"])
        
        logger.debug(f"Retrieved {len(all_media)} media items for {len(tweet_ids)} tweets")
        return all_media
    except Exception as e:
        logger.error(f"Error retrieving extracted media for tweets: {e}")
        raise