"""
Generic S3-compatible media storage backend for tweet media downloads.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Dict, List, Optional

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from mindvault.bookmarks.twitter.extract import (
    ExtractedMedia,
    ExtractedMediaList,
)
from mindvault.bookmarks.twitter.media_download import (
    build_media_key,
    download_media,
)
from mindvault.core.config import BlobStorageConnection, settings
from mindvault.core.logger_setup import logger

# S3 multipart upload requires minimum 5MB per part (except last).
MULTIPART_THRESHOLD = 5 * 1024 * 1024  # 5 MiB
_MISSING_BUCKET_ERROR_CODES = {"404", "NoSuchBucket", "NotFound"}
_MISSING_OBJECT_ERROR_CODES = {"404", "NoSuchKey", "NotFound"}


def build_s3_uri(bucket_name: str, key: str) -> str:
    """Build canonical object location URI."""
    return f"s3://{bucket_name}/{key}"


def _create_s3_session(connection: BlobStorageConnection) -> aioboto3.Session:
    return aioboto3.Session(
        aws_access_key_id=connection.access_key,
        aws_secret_access_key=connection.secret_key,
        region_name=connection.region,
    )


def _create_s3_client_config(connection: BlobStorageConnection) -> Config:
    return Config(
        s3={"addressing_style": connection.addressing_style},
        retries={"max_attempts": 5, "mode": "standard"},
    )


async def _ensure_bucket_exists(
    s3_client,
    connection: BlobStorageConnection,
) -> None:
    bucket_name = connection.bucket_name
    try:
        await s3_client.head_bucket(Bucket=bucket_name)
        return
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", "")).strip()
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        is_missing_bucket = (
            error_code in _MISSING_BUCKET_ERROR_CODES
            or status_code == 404
        )

        if not is_missing_bucket:
            raise

        if not connection.auto_create_bucket:
            raise ConnectionError(
                f"Bucket '{bucket_name}' does not exist in provider '{connection.provider}' "
                "and BLOB_STORAGE_AUTO_CREATE_BUCKET is disabled."
            ) from exc

    logger.info(f"Creating bucket '{bucket_name}' in provider '{connection.provider}'")
    await s3_client.create_bucket(Bucket=bucket_name)


async def _check_object_exists(s3_client, bucket_name: str, key: str) -> bool:
    try:
        response = await s3_client.head_object(Bucket=bucket_name, Key=key)
        return response.get("ContentLength", 0) > 0
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", "")).strip()
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if error_code in _MISSING_OBJECT_ERROR_CODES or status_code == 404:
            return False
        raise


def _guess_content_type(key: str) -> Optional[str]:
    ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    content_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "mp4": "video/mp4",
        "webp": "image/webp",
    }
    return content_types.get(ext)


async def _upload_stream_to_s3_compatible(
    s3_client,
    stream: AsyncIterator[bytes],
    bucket_name: str,
    key: str,
    content_type: Optional[str] = None,
) -> bool:
    multipart_upload = await s3_client.create_multipart_upload(
        Bucket=bucket_name,
        Key=key,
        ContentType=content_type or "application/octet-stream",
    )
    upload_id = multipart_upload["UploadId"]

    parts = []
    part_number = 1
    buffer = bytearray()

    try:
        async for chunk in stream:
            if not chunk:
                continue
            buffer.extend(chunk)

            while len(buffer) >= MULTIPART_THRESHOLD:
                part_data = bytes(buffer[:MULTIPART_THRESHOLD])
                del buffer[:MULTIPART_THRESHOLD]

                part_response = await s3_client.upload_part(
                    Bucket=bucket_name,
                    Key=key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=part_data,
                )
                parts.append({
                    "PartNumber": part_number,
                    "ETag": part_response["ETag"],
                })
                part_number += 1

        if buffer:
            part_response = await s3_client.upload_part(
                Bucket=bucket_name,
                Key=key,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=bytes(buffer),
            )
            parts.append({
                "PartNumber": part_number,
                "ETag": part_response["ETag"],
            })

        if not parts:
            await s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=key,
                UploadId=upload_id,
            )
            logger.error(f"Empty file received for {key}, skipping upload")
            return False

        await s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
        )
        return True
    except asyncio.CancelledError:
        try:
            await s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=key,
                UploadId=upload_id,
            )
        except Exception:
            pass
        raise
    except Exception:
        try:
            await s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=key,
                UploadId=upload_id,
            )
        except Exception:
            pass
        raise


class S3CompatibleMediaStore:
    """S3-compatible media storage backend (MinIO-only in this release)."""

    def __init__(
        self,
        *,
        provider: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> None:
        self.connection = settings.get_blob_storage_connection(
            provider=provider,
            bucket_name=bucket_name,
        )
        self._session = _create_s3_session(self.connection)
        self._client_cm = None
        self.s3_client = None

    async def __aenter__(self) -> "S3CompatibleMediaStore":
        self._client_cm = self._session.client(
            "s3",
            endpoint_url=self.connection.endpoint_url,
            verify=self.connection.verify_ssl,
            config=_create_s3_client_config(self.connection),
        )
        self.s3_client = await self._client_cm.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client_cm is not None:
            await self._client_cm.__aexit__(exc_type, exc, tb)

    async def prepare(self) -> None:
        if self.s3_client is None:
            raise RuntimeError("S3CompatibleMediaStore must be used as an async context manager")
        await _ensure_bucket_exists(self.s3_client, self.connection)

    def get_location(self, item: ExtractedMedia) -> str:
        key = build_media_key(item)
        return build_s3_uri(self.connection.bucket_name, key)

    async def exists(self, item: ExtractedMedia) -> bool:
        if self.s3_client is None:
            raise RuntimeError("S3CompatibleMediaStore must be used as an async context manager")
        key = build_media_key(item)
        return await _check_object_exists(self.s3_client, self.connection.bucket_name, key)

    async def save(
        self,
        item: ExtractedMedia,
        stream: AsyncIterator[bytes],
        *,
        content_type: Optional[str] = None,
    ) -> str:
        if self.s3_client is None:
            raise RuntimeError("S3CompatibleMediaStore must be used as an async context manager")
        key = build_media_key(item)
        inferred_type = content_type or _guess_content_type(key)
        success = await _upload_stream_to_s3_compatible(
            s3_client=self.s3_client,
            stream=stream,
            bucket_name=self.connection.bucket_name,
            key=key,
            content_type=inferred_type,
        )
        if not success:
            raise IOError(f"Upload failed for {key}")
        return build_s3_uri(self.connection.bucket_name, key)


async def download_tweet_media_to_blob_storage(
    media_list: ExtractedMediaList,
    *,
    provider: Optional[str] = None,
    bucket_name: Optional[str] = None,
    **kwargs,
) -> Dict[str, List[str]]:
    """
    Download tweet media and save to configured S3-compatible blob storage.
    """
    async with S3CompatibleMediaStore(provider=provider, bucket_name=bucket_name) as store:
        results = await download_media(
            media_list=media_list,
            store=store,
            progress_desc=f"Uploading {len(media_list.media)} media files to {store.connection.provider}",
            **kwargs,
        )

    normalized_results: Dict[str, List[str]] = {}
    for tweet_id, locations in results.items():
        normalized_results[tweet_id] = [str(location) for location in locations]
    return normalized_results
