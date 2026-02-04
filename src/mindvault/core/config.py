"""Configuration settings for the MindVault Twitter application.

This module contains the shared configuration settings used across the application.
"""

from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    Attributes:
        twitter_ct0: Twitter ct0 cookie value for authentication
        twitter_auth_token: Twitter auth token for authentication
        twitter_scraper_ct0: Optional separate Twitter ct0 cookie for tweet scraping
        twitter_scraper_auth_token: Optional separate Twitter auth token for tweet scraping
        bookmarks_path: Directory path for storing bookmarks data
        tweet_ids_path: Directory path for storing tweet IDs
        tweet_data_dir: Directory path for storing tweet data
        extracted_data_dir: Directory path for storing extracted tweet data
        media_dir: Directory path for storing downloaded media from tweets
        database_url: SQLite database URL
        pending_tweets_path: Path for storing pending tweets
    """
    
    twitter_ct0: str
    twitter_auth_token: str
    twitter_scraper_ct0: str = ""
    twitter_scraper_auth_token: str = ""
    
    # Get the user's home directory and create .mindvault base directory
    base_dir: Path = Path.home() / ".mindvault"
    
    # Define all paths relative to the base directory
    bookmarks_path: Path = base_dir / "twitter/bookmarks"
    tweet_ids_path: Path = base_dir / "twitter/tweet_ids"
    tweet_data_dir: Path = base_dir / "twitter/tweet_data"
    extracted_data_dir: Path = base_dir / "twitter/extracted_data"
    media_dir: Path = base_dir / "twitter/media"
    database_url: str = f"sqlite:////{base_dir / 'twitter/tweets.db'}"
    pending_tweets_path: Path = base_dir / "twitter/pending_tweets.json"
    mongodb_uri: str = "mongodb://localhost:27017/"
    db_name: str = "mindvault"
    raw_data_collection: str = "raw-data"
    extracted_data_collection: str = "extracted-data"
    scraper_collection: str = "scraper"
    bookmarks_collection: str = "bookmarks"

    # RustFS / S3-compatible object storage settings
    rustfs_endpoint_url: str = "http://localhost:9000"
    rustfs_access_key: str = "rustfsadmin"
    rustfs_secret_key: str = "rustfsadmin"
    rustfs_bucket_name: str = "mindvault-media"
    rustfs_region: str = "us-east-1"

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    def __init__(self, **kwargs):
        """Initialize settings and set up required resources."""
        super().__init__(**kwargs)
        self.setup_directories()
        self.validate_mongodb_connection()

    def setup_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.bookmarks_path.mkdir(parents=True, exist_ok=True)
        self.tweet_ids_path.mkdir(parents=True, exist_ok=True)
        self.tweet_data_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_data_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.pending_tweets_path.parent.mkdir(parents=True, exist_ok=True)

    def get_bookmarks_auth(self) -> dict:
        """Get authentication details for bookmarks export.
        
        Returns:
            Dictionary with Twitter authentication cookies
        """
        return {
            "ct0": self.twitter_ct0,
            "auth_token": self.twitter_auth_token,
        }
    
    def get_scraper_auth(self) -> dict:
        """Get authentication details for tweet scraping.
        
        If scraper-specific credentials are provided, use those.
        Otherwise, fall back to the main credentials.
        
        Returns:
            Dictionary with Twitter authentication cookies
        """
        if self.twitter_scraper_ct0 and self.twitter_scraper_auth_token:
            return {
                "ct0": self.twitter_scraper_ct0,
                "auth_token": self.twitter_scraper_auth_token,
            }
        return self.get_bookmarks_auth()

    def validate_mongodb_connection(self) -> bool:
        """Validates the connection to MongoDB.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            client = MongoClient(self.mongodb_uri)
            client.admin.command('ping')  # Send a ping command to test connection
            return True
        except ConnectionFailure:
            raise ConnectionError("Failed to connect to MongoDB. Please check your connection settings.")

    def validate_rustfs_connection(self) -> bool:
        """Validates the connection to RustFS (S3-compatible storage).

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            s3_client = boto3.client(
                "s3",
                endpoint_url=self.rustfs_endpoint_url,
                aws_access_key_id=self.rustfs_access_key,
                aws_secret_access_key=self.rustfs_secret_key,
                region_name=self.rustfs_region,
            )
            s3_client.list_buckets()
            return True
        except (BotoCoreError, ClientError, Exception):
            raise ConnectionError(
                f"Failed to connect to RustFS at {self.rustfs_endpoint_url}. "
                "Please check your connection settings and ensure RustFS is running."
            )

settings = Settings()
