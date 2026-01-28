"""
Module for downloading media from Twitter tweets and uploading to RustFS (S3-compatible storage).

This is a parallel module to download_tweet_media.py. It downloads media from Twitter
using httpx and uploads to RustFS via aioboto3 instead of writing to the local filesystem.
"""

import asyncio
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Generator
from urllib.parse import urlsplit
import functools

import aioboto3
from httpx import AsyncClient
from tqdm.asyncio import tqdm_asyncio

from mindvault.bookmarks.twitter.extract import (
    ExtractedMediaList,
    ExtractedMedia,
)
from mindvault.bookmarks.twitter.download_tweet_media import (
    USER_AGENTS,
    _create_http_client,
)
from mindvault.core.config import settings
from mindvault.core.logger_setup import logger


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

    The file content is streamed into a BytesIO buffer, then uploaded
    to S3 via upload_fileobj. This avoids writing to the local filesystem.

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

    url = item.media_url
    retry_count = 0

    while retry_count <= max_retries:
        try:
            buffer = BytesIO()
            async with http_client.stream("GET", url) as response:
                response.raise_for_status()
                async for chunk in response.aiter_raw(chunk_size):
                    buffer.write(chunk)

            buffer.seek(0)

            content_type = _guess_content_type(s3_key)
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            await s3_client.upload_fileobj(
                Fileobj=buffer,
                Bucket=bucket_name,
                Key=s3_key,
                ExtraArgs=extra_args,
            )

            logger.debug(f"Uploaded {s3_key} to {bucket_name}")
            return (item.tweet_id, s3_key)

        except Exception as e:
            retry_count += 1
            if retry_count > max_retries:
                logger.error(
                    f"Failed to download/upload {url} after {max_retries} retries: {e}"
                )
                return (item.tweet_id, None)

            logger.warning(
                f"Error processing {url} (attempt {retry_count}/{max_retries}): {e}"
            )
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
        process_single_tweet_file,
        extract_media_info_from_conversation,
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
