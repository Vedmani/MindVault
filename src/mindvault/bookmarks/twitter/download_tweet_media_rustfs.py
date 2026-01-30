"""
Module for downloading media from Twitter tweets and uploading to RustFS (S3-compatible storage).

This is a parallel module to download_tweet_media.py. It downloads media from Twitter
using httpx and uploads to RustFS via aioboto3 instead of writing to the local filesystem.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit

import aioboto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError
from httpx import AsyncClient
from tqdm.asyncio import tqdm_asyncio

from mindvault.bookmarks.twitter.download_tweet_media import (
    _create_http_client,
    _download_media_stream,
)
from mindvault.bookmarks.twitter.extract import (
    ExtractedMedia,
    ExtractedMediaList,
)
from mindvault.core.config import settings
from mindvault.core.logger_setup import logger

# S3 multipart upload requires minimum 5MB per part (except last)
MULTIPART_THRESHOLD = 5 * 1024 * 1024  # 5 MiB


def get_s3_key(item: ExtractedMedia) -> str:
    """
    Compute the S3 object key for a media item.

    Mirrors the filesystem path structure: {tweet_id}/{media_id}.{ext}

    Args:
        item: ExtractedMedia object with tweet_id, media_id, and media_url.

    Returns:
        S3 object key string, e.g. "1895195365269467454/abc123.jpg"
    """
    url = item.media_url
    ext = urlsplit(url).path.split("/")[-1].split("?")[0]
    filename = f"{item.media_id}"
    if "." not in filename and "." in ext:
        filename = f"{filename}.{ext.split('.')[-1]}"
    return f"{item.tweet_id}/{filename}"


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
    http_client: AsyncClient,
    s3_client,
    url: str,
    bucket_name: str,
    s3_key: str,
    chunk_size: int = 32768,
    content_type: Optional[str] = None,
) -> bool:
    """
    Stream download from URL directly to RustFS using multipart upload.

    Memory usage: ~10MB peak (buffer + copy during upload), regardless of file size.

    Args:
        http_client: httpx AsyncClient for downloading.
        s3_client: aioboto3 S3 client for uploading.
        url: URL to download from.
        bucket_name: Target S3 bucket.
        s3_key: Object key.
        chunk_size: Chunk size for HTTP streaming.
        content_type: Optional MIME type.

    Returns:
        True on success, False on failure.
    """
    # Start multipart upload
    mpu = await s3_client.create_multipart_upload(
        Bucket=bucket_name,
        Key=s3_key,
        ContentType=content_type or "application/octet-stream"
    )
    upload_id = mpu['UploadId']

    parts = []
    part_number = 1
    buffer = bytearray()

    try:
        async for chunk in _download_media_stream(http_client, url, chunk_size):
            buffer.extend(chunk)

            # When buffer reaches part size, upload it
            while len(buffer) >= MULTIPART_THRESHOLD:
                part_data = bytes(buffer[:MULTIPART_THRESHOLD])
                buffer = buffer[MULTIPART_THRESHOLD:]

                resp = await s3_client.upload_part(
                    Bucket=bucket_name,
                    Key=s3_key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=part_data
                )
                parts.append({
                    'PartNumber': part_number,
                    'ETag': resp['ETag']
                })
                part_number += 1

        # Upload remaining data as final part (no minimum size for last part)
        if buffer:
            resp = await s3_client.upload_part(
                Bucket=bucket_name,
                Key=s3_key,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=bytes(buffer)
            )
            parts.append({
                'PartNumber': part_number,
                'ETag': resp['ETag']
            })

        # Handle empty file case - abort multipart, log error, skip upload
        if not parts:
            await s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=s3_key,
                UploadId=upload_id
            )
            logger.error(f"Empty file received for {s3_key}, skipping upload")
            return False

        # Complete the upload
        await s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=s3_key,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )

        logger.debug(f"Uploaded {s3_key} to {bucket_name} ({len(parts)} parts)")
        return True

    except Exception as e:
        # Abort on any failure to avoid orphaned parts
        try:
            await s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=s3_key,
                UploadId=upload_id
            )
        except Exception:
            pass  # Best effort cleanup
        raise  # Re-raise for caller to handle retry


async def _upload_single_file(
    http_client: AsyncClient,
    s3_client,
    item: ExtractedMedia,
    bucket_name: str,
    chunk_size: int = 32768,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    skip_existing: bool = True,
) -> Tuple[str, Optional[str]]:
    """
    Download a media file from Twitter and upload it to RustFS.

    Args:
        http_client: httpx AsyncClient for downloading from Twitter.
        s3_client: aioboto3 S3 client for uploading to RustFS.
        item: ExtractedMedia describing the media to download.
        bucket_name: Target S3 bucket.
        chunk_size: Chunk size for HTTP streaming.
        max_retries: Maximum retry attempts on failure.
        retry_delay: Base delay between retries (multiplied by attempt number).
        skip_existing: If True, skip upload when the object already exists in the bucket.

    Returns:
        Tuple of (tweet_id, s3_key) on success, or (tweet_id, None) on failure.
    """
    s3_key = get_s3_key(item)

    if skip_existing and await _check_object_exists(s3_client, bucket_name, s3_key):
        logger.debug(f"Object already exists, skipping: {bucket_name}/{s3_key}")
        return (item.tweet_id, s3_key)

    content_type = _guess_content_type(s3_key)

    retry_count = 0
    while retry_count <= max_retries:
        try:
            success = await _upload_stream_to_rustfs(
                http_client=http_client,
                s3_client=s3_client,
                url=item.media_url,
                bucket_name=bucket_name,
                s3_key=s3_key,
                chunk_size=chunk_size,
                content_type=content_type,
            )
            if success:
                return (item.tweet_id, s3_key)
            return (item.tweet_id, None)

        except (httpx.HTTPError, IOError, BotoCoreError, ClientError) as e:
            retry_count += 1
            if retry_count > max_retries:
                logger.error(f"Failed to upload {s3_key} after {max_retries} retries: {e}")
                return (item.tweet_id, None)
            logger.warning(f"Error uploading {s3_key} (attempt {retry_count}/{max_retries}): {e}")
            await asyncio.sleep(retry_delay * retry_count)

    return (item.tweet_id, None)


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
    if not media_list.media:
        logger.warning("No media items to download")
        return {}

    bucket = bucket_name or settings.rustfs_bucket_name

    session = _create_s3_session()

    async with session.client(
        "s3",
        endpoint_url=settings.rustfs_endpoint_url,
    ) as s3_client:
        await _ensure_bucket_exists(s3_client, bucket)

        async with await _create_http_client(
            max_connections=kwargs.get("max_connections", 50),
            max_keepalive_connections=kwargs.get("max_keepalive_connections"),
            keepalive_expiry=kwargs.get("keepalive_expiry", 5.0),
            timeout=kwargs.get("timeout", 60),
        ) as http_client:
            tasks = [
                _upload_single_file(
                    http_client=http_client,
                    s3_client=s3_client,
                    item=item,
                    bucket_name=bucket,
                    chunk_size=kwargs.get("chunk_size", 32768),
                    max_retries=kwargs.get("max_retries", 3),
                    retry_delay=kwargs.get("retry_delay", 1.0),
                    skip_existing=kwargs.get("skip_existing", True),
                )
                for item in media_list.media
            ]

            results = await tqdm_asyncio.gather(
                *tasks,
                desc=f"Uploading {len(media_list.media)} media files to RustFS",
            )

    upload_results: Dict[str, List[str]] = {}
    for tweet_id, s3_key in results:
        if s3_key:
            if tweet_id not in upload_results:
                upload_results[tweet_id] = []
            upload_results[tweet_id].append(s3_key)

    return upload_results


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
