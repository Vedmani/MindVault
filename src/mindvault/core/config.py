"""Configuration settings for the MindVault Twitter application."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Literal, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

BlobStorageProvider = Literal["minio"]
BlobStorageAddressingStyle = Literal["auto", "virtual", "path"]

_VALID_ADDRESSING_STYLES = {"auto", "virtual", "path"}
_BLOB_STORAGE_PROVIDER_DEFAULTS: Dict[str, Dict[str, object]] = {
    "minio": {
        "endpoint_url": "http://localhost:9000",
        "access_key": "minioadmin",
        "secret_key": "minioadmin",
        "bucket_name": "mindvault-media",
        "region": "us-east-1",
        "addressing_style": "path",
        "verify_ssl": False,
        "auto_create_bucket": True,
    },
}


@dataclass(frozen=True)
class BlobStorageConnection:
    """Resolved object storage connection settings."""

    provider: BlobStorageProvider
    endpoint_url: str
    access_key: str
    secret_key: str
    bucket_name: str
    region: str
    addressing_style: BlobStorageAddressingStyle
    verify_ssl: bool
    auto_create_bucket: bool


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    twitter_ct0: str
    twitter_auth_token: str
    twitter_scraper_ct0: str = ""
    twitter_scraper_auth_token: str = ""

    base_dir: Path = Path.home() / ".mindvault"

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

    blob_storage_provider: BlobStorageProvider = "minio"
    blob_storage_endpoint_url: Optional[str] = None
    blob_storage_access_key: Optional[str] = None
    blob_storage_secret_key: Optional[str] = None
    blob_storage_bucket_name: Optional[str] = None
    blob_storage_region: Optional[str] = None
    blob_storage_addressing_style: Optional[str] = None
    blob_storage_verify_ssl: Optional[bool] = None
    blob_storage_auto_create_bucket: Optional[bool] = None

    # If needed for local scripts/tests, this can be disabled via env:
    # VALIDATE_EXTERNAL_SERVICES_ON_STARTUP=false
    validate_external_services_on_startup: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def __init__(self, validate_on_startup: Optional[bool] = None, **kwargs):
        """Initialize settings and validate external dependencies."""
        super().__init__(**kwargs)
        self.setup_directories()

        should_validate = (
            self.validate_external_services_on_startup
            if validate_on_startup is None
            else validate_on_startup
        )
        if should_validate:
            self.validate_mongodb_connection()
            self.validate_blob_storage_connection()

    def setup_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.bookmarks_path.mkdir(parents=True, exist_ok=True)
        self.tweet_ids_path.mkdir(parents=True, exist_ok=True)
        self.tweet_data_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_data_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.pending_tweets_path.parent.mkdir(parents=True, exist_ok=True)

    def get_bookmarks_auth(self) -> dict:
        """Get authentication details for bookmarks export."""
        return {
            "ct0": self.twitter_ct0,
            "auth_token": self.twitter_auth_token,
        }

    def get_scraper_auth(self) -> dict:
        """Get authentication details for tweet scraping."""
        if self.twitter_scraper_ct0 and self.twitter_scraper_auth_token:
            return {
                "ct0": self.twitter_scraper_ct0,
                "auth_token": self.twitter_scraper_auth_token,
            }
        return self.get_bookmarks_auth()

    def _resolve_blob_provider(self, provider: Optional[str] = None) -> BlobStorageProvider:
        provider_name = (provider or self.blob_storage_provider).strip().lower()
        if provider_name not in _BLOB_STORAGE_PROVIDER_DEFAULTS:
            valid = ", ".join(sorted(_BLOB_STORAGE_PROVIDER_DEFAULTS.keys()))
            raise ValueError(f"Invalid blob storage provider '{provider_name}'. Valid providers: {valid}")
        return provider_name  # type: ignore[return-value]

    def get_blob_storage_connection(
        self,
        *,
        provider: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> BlobStorageConnection:
        """Resolve effective blob storage config with deterministic precedence."""
        resolved_provider = self._resolve_blob_provider(provider)
        defaults = _BLOB_STORAGE_PROVIDER_DEFAULTS[resolved_provider]
        endpoint_url = self.blob_storage_endpoint_url or str(defaults["endpoint_url"])
        access_key = self.blob_storage_access_key or str(defaults["access_key"])
        secret_key = self.blob_storage_secret_key or str(defaults["secret_key"])
        resolved_bucket_name = self.blob_storage_bucket_name or str(defaults["bucket_name"])
        region = self.blob_storage_region or str(defaults["region"])

        if bucket_name is not None and bucket_name != "":
            resolved_bucket_name = bucket_name

        addressing_style = (
            self.blob_storage_addressing_style
            if self.blob_storage_addressing_style is not None
            else str(defaults["addressing_style"])
        )
        if addressing_style not in _VALID_ADDRESSING_STYLES:
            raise ValueError(
                "Invalid BLOB_STORAGE_ADDRESSING_STYLE value "
                f"'{addressing_style}'. Valid values: auto, virtual, path"
            )

        verify_ssl = (
            self.blob_storage_verify_ssl
            if self.blob_storage_verify_ssl is not None
            else bool(defaults["verify_ssl"])
        )
        auto_create_bucket = (
            self.blob_storage_auto_create_bucket
            if self.blob_storage_auto_create_bucket is not None
            else bool(defaults["auto_create_bucket"])
        )

        return BlobStorageConnection(
            provider=resolved_provider,
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            bucket_name=resolved_bucket_name,
            region=region,
            addressing_style=addressing_style,  # type: ignore[arg-type]
            verify_ssl=verify_ssl,
            auto_create_bucket=auto_create_bucket,
        )

    def validate_mongodb_connection(self) -> bool:
        """Validate the connection to MongoDB."""
        try:
            client = MongoClient(self.mongodb_uri)
            client.admin.command("ping")
            return True
        except ConnectionFailure as exc:
            raise ConnectionError(
                "Failed to connect to MongoDB. Please check your connection settings."
            ) from exc

    def validate_blob_storage_connection(self, *, provider: Optional[str] = None) -> bool:
        """Validate the selected object storage provider connection."""
        connection = self.get_blob_storage_connection(provider=provider)
        try:
            client_config = Config(
                s3={"addressing_style": connection.addressing_style},
                retries={"max_attempts": 3, "mode": "standard"},
            )
            s3_client = boto3.client(
                "s3",
                endpoint_url=connection.endpoint_url,
                aws_access_key_id=connection.access_key,
                aws_secret_access_key=connection.secret_key,
                region_name=connection.region,
                verify=connection.verify_ssl,
                config=client_config,
            )
            s3_client.list_buckets()
            return True
        except (BotoCoreError, ClientError, Exception) as exc:
            raise ConnectionError(
                "Failed to connect to blob storage provider "
                f"'{connection.provider}' at {connection.endpoint_url}. "
                "Please check your object storage configuration and service availability."
            ) from exc

settings = Settings()
