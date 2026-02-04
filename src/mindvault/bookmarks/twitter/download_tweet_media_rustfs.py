"""
Module for downloading media from Twitter tweets and uploading to RustFS (S3-compatible storage).

This is a parallel module to download_tweet_media.py. It downloads media from Twitter
and uploads to RustFS via aioboto3 instead of writing to the local filesystem.
"""

import asyncio
from typing import AsyncIterator, Dict, List, Optional

import aioboto3

from mindvault.bookmarks.twitter.media_download import (
    build_media_key,
    download_media,
)
from mindvault.bookmarks.twitter.extract import (
    ExtractedMedia,
    ExtractedMediaList,
)
from mindvault.core.config import settings
from mindvault.core.logger_setup import logger

# S3 multipart upload requires minimum 5MB per part (except last)
MULTIPART_THRESHOLD = 5 * 1024 * 1024  # 5 MiB


def _create_s3_session() -> aioboto3.Session:
    """
    Create an aioboto3 session configured for RustFS.

    Returns:
        Configured aioboto3 Session.
    """
    return aioboto3.Session(
        aws_access_key_id=settings.rustfs_access_key,
        aws_secret_access_key=settings.rustfs_secret_key,
        region_name=settings.rustfs_region,
    )


async def _ensure_bucket_exists(s3_client, bucket_name: str) -> None:
    """
    Create the S3 bucket if it does not already exist.

    Args:
        s3_client: Active aioboto3 S3 client.
        bucket_name: Name of the bucket to create.
    """
    try:
        await s3_client.head_bucket(Bucket=bucket_name)
        logger.debug(f"Bucket '{bucket_name}' already exists")
    except Exception:
        logger.info(f"Creating bucket '{bucket_name}'")
        await s3_client.create_bucket(Bucket=bucket_name)


async def _check_object_exists(s3_client, bucket_name: str, key: str) -> bool:
    """
    Check whether an S3 object already exists and has non-zero size.

    Args:
        s3_client: Active aioboto3 S3 client.
        bucket_name: Bucket name.
        key: Object key.

    Returns:
        True if the object exists with size > 0.
    """
    try:
        response = await s3_client.head_object(Bucket=bucket_name, Key=key)
        return response.get("ContentLength", 0) > 0
    except Exception:
        return False


def _guess_content_type(key: str) -> Optional[str]:
    """
    Guess MIME content type from an S3 key's file extension.

    Args:
        key: S3 object key (e.g. "12345/media.jpg").

    Returns:
        MIME type string, or None if unknown.
    """
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


async def _upload_stream_to_rustfs(
    s3_client,
    stream: AsyncIterator[bytes],
    bucket_name: str,
    s3_key: str,
    content_type: Optional[str] = None,
) -> bool:
    """
    Stream upload to RustFS using multipart upload.

    Memory usage remains bounded by the multipart threshold size.
    """
    mpu = await s3_client.create_multipart_upload(
        Bucket=bucket_name,
        Key=s3_key,
        ContentType=content_type or "application/octet-stream",
    )
    upload_id = mpu["UploadId"]

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

                resp = await s3_client.upload_part(
                    Bucket=bucket_name,
                    Key=s3_key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=part_data,
                )
                parts.append({
                    "PartNumber": part_number,
                    "ETag": resp["ETag"],
                })
                part_number += 1

        if buffer:
            resp = await s3_client.upload_part(
                Bucket=bucket_name,
                Key=s3_key,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=bytes(buffer),
            )
            parts.append({
                "PartNumber": part_number,
                "ETag": resp["ETag"],
            })

        if not parts:
            await s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=s3_key,
                UploadId=upload_id,
            )
            logger.error(f"Empty file received for {s3_key}, skipping upload")
            return False

        await s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=s3_key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
        )

        logger.debug(f"Uploaded {s3_key} to {bucket_name} ({len(parts)} parts)")
        return True

    except Exception:
        try:
            await s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=s3_key,
                UploadId=upload_id,
            )
        except Exception:
            pass
        raise


class RustFSMediaStore:
    """RustFS-backed media storage using S3-compatible API."""

    def __init__(self, bucket_name: Optional[str] = None) -> None:
        self.bucket_name = bucket_name or settings.rustfs_bucket_name
        self._session = _create_s3_session()
        self._client_cm = None
        self.s3_client = None

    async def __aenter__(self) -> "RustFSMediaStore":
        self._client_cm = self._session.client(
            "s3",
            endpoint_url=settings.rustfs_endpoint_url,
        )
        self.s3_client = await self._client_cm.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client_cm is not None:
            await self._client_cm.__aexit__(exc_type, exc, tb)

    async def prepare(self) -> None:
        if self.s3_client is None:
            raise RuntimeError("RustFSMediaStore must be used as an async context manager")
        settings.validate_rustfs_connection()
        await _ensure_bucket_exists(self.s3_client, self.bucket_name)

    def get_location(self, item: ExtractedMedia) -> str:
        return build_media_key(item)

    async def exists(self, item: ExtractedMedia) -> bool:
        if self.s3_client is None:
            raise RuntimeError("RustFSMediaStore must be used as an async context manager")
        key = build_media_key(item)
        return await _check_object_exists(self.s3_client, self.bucket_name, key)

    async def save(
        self,
        item: ExtractedMedia,
        stream: AsyncIterator[bytes],
        *,
        content_type: Optional[str] = None,
    ) -> str:
        if self.s3_client is None:
            raise RuntimeError("RustFSMediaStore must be used as an async context manager")
        s3_key = build_media_key(item)
        inferred_type = content_type or _guess_content_type(s3_key)

        success = await _upload_stream_to_rustfs(
            s3_client=self.s3_client,
            stream=stream,
            bucket_name=self.bucket_name,
            s3_key=s3_key,
            content_type=inferred_type,
        )
        if not success:
            raise IOError(f"Upload failed for {s3_key}")

        return s3_key


async def download_tweet_media_to_rustfs(
    media_list: ExtractedMediaList,
    bucket_name: Optional[str] = None,
    **kwargs,
) -> Dict[str, List[str]]:
    """
    Download media from Twitter tweets and upload to RustFS.

    This is the RustFS equivalent of download_tweet_media(). It accepts
    the same ExtractedMediaList input but returns S3 keys instead of Paths.

    Args:
        media_list: ExtractedMediaList from extract_media_info_from_conversation.
        bucket_name: Target S3 bucket (defaults to settings.rustfs_bucket_name).
        **kwargs: Additional keyword arguments:
            - chunk_size: Size of chunks when downloading files (default: 32768)
            - max_connections: Maximum number of concurrent HTTP connections (default: 50)
            - max_keepalive_connections: Max keepalive connections for HTTP
            - keepalive_expiry: HTTP keepalive expiry in seconds (default: 5.0)
            - max_retries: Maximum retry attempts (default: 3)
            - retry_delay: Base retry delay in seconds (default: 1.0)
            - timeout: HTTP timeout in seconds (default: 60)
            - skip_existing: Skip if object already exists in bucket (default: True)

    Returns:
        Dictionary mapping tweet IDs to lists of S3 keys for successfully uploaded media.
    """
    async with RustFSMediaStore(bucket_name=bucket_name) as store:
        results = await download_media(
            media_list=media_list,
            store=store,
            progress_desc=f"Uploading {len(media_list.media)} media files to RustFS",
            **kwargs,
        )

    return results


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from mindvault.bookmarks.twitter.extract import (
        extract_media_info_from_conversation,
        process_single_tweet_file,
    )

    async def main():
        tweet_file = Path("artifacts/tweet_data/1895195365269467454.json")
        tweet_file_2 = Path("artifacts/tweet_data/1894346156656005380.json")

        conversation = process_single_tweet_file(tweet_file)
        conversation_2 = process_single_tweet_file(tweet_file_2)

        if conversation:
            media_list = extract_media_info_from_conversation(
                conversation, extract_card_images=False
            )
            media_list_2 = extract_media_info_from_conversation(
                conversation_2, extract_card_images=False
            )
            media_list.media.extend(media_list_2.media)

            results = await download_tweet_media_to_rustfs(
                media_list=media_list,
                max_connections=50,
            )
            print(f"Uploaded media to RustFS: {results}")

    asyncio.run(main())
