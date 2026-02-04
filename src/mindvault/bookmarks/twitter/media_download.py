"""
Shared streaming download utilities and storage abstraction for tweet media.
"""

from __future__ import annotations

import asyncio
import random
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional, Protocol, Tuple, Union
from urllib.parse import urlsplit

from httpx import AsyncClient, Limits
from tqdm.asyncio import tqdm_asyncio

from mindvault.bookmarks.twitter.extract import ExtractedMedia, ExtractedMediaList
from mindvault.core.logger_setup import logger

MediaLocation = Union[str, Path]

# User agents to randomize requests
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
]


class MediaStore(Protocol):
    """Storage backend interface for downloaded media."""

    async def prepare(self) -> None:
        """Prepare backend resources (e.g. create directories or buckets)."""

    def get_location(self, item: ExtractedMedia) -> MediaLocation:
        """Return the storage location for the given media item."""

    async def exists(self, item: ExtractedMedia) -> bool:
        """Check whether the item already exists in storage."""

    async def save(
        self,
        item: ExtractedMedia,
        stream: AsyncIterator[bytes],
        *,
        content_type: Optional[str] = None,
    ) -> MediaLocation:
        """Save streamed media into storage."""


async def _create_http_client(
    max_connections: int = 50,
    max_keepalive_connections: Optional[int] = None,
    keepalive_expiry: float = 5.0,
    timeout: int = 60,
    user_agent: Optional[str] = None,
) -> AsyncClient:
    """
    Create an HTTP client for downloading media.
    """
    if max_keepalive_connections is None:
        max_keepalive_connections = max_connections

    limits = Limits(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive_connections,
        keepalive_expiry=keepalive_expiry,
    )

    headers = {"user-agent": user_agent or random.choice(USER_AGENTS)}

    return AsyncClient(
        limits=limits,
        headers=headers,
        http2=True,
        verify=True,
        timeout=timeout,
        follow_redirects=True,
    )


def build_media_key(item: ExtractedMedia) -> str:
    """
    Build a storage key/path for a media item.

    Format: {tweet_id}/{media_id}.{ext}
    """
    url = item.media_url
    ext = urlsplit(url).path.split("/")[-1].split("?")[0]
    filename = f"{item.media_id}"
    if "." not in filename and "." in ext:
        filename = f"{filename}.{ext.split('.')[-1]}"
    return f"{item.tweet_id}/{filename}"


async def download_media_stream(
    client: AsyncClient,
    url: str,
    chunk_size: int = 32768,
) -> AsyncIterator[bytes]:
    """
    Stream media from a URL without buffering the entire response in memory.
    """
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        async for chunk in response.aiter_raw(chunk_size):
            if chunk:
                yield chunk


async def download_media(
    media_list: ExtractedMediaList,
    store: MediaStore,
    **kwargs,
) -> Dict[str, List[MediaLocation]]:
    """
    Download media items and save them using the provided storage backend.
    """
    if not media_list.media:
        logger.warning("No media items to download")
        return {}

    chunk_size = kwargs.get("chunk_size", 32768)
    max_retries = kwargs.get("max_retries", 3)
    retry_delay = kwargs.get("retry_delay", 1.0)
    skip_existing = kwargs.get("skip_existing", True)
    progress_desc = kwargs.get(
        "progress_desc",
        f"Downloading {len(media_list.media)} media files",
    )

    await store.prepare()

    async with await _create_http_client(
        max_connections=kwargs.get("max_connections", 50),
        max_keepalive_connections=kwargs.get("max_keepalive_connections"),
        keepalive_expiry=kwargs.get("keepalive_expiry", 5.0),
        timeout=kwargs.get("timeout", 60),
    ) as client:
        async def _download_single(item: ExtractedMedia) -> Tuple[str, Optional[MediaLocation]]:
            if skip_existing and await store.exists(item):
                location = store.get_location(item)
                logger.debug(f"Media already exists, skipping: {location}")
                return (item.tweet_id, location)

            retry_count = 0
            while retry_count <= max_retries:
                try:
                    stream = download_media_stream(
                        client=client,
                        url=item.media_url,
                        chunk_size=chunk_size,
                    )
                    saved_location = await store.save(
                        item=item,
                        stream=stream,
                        content_type=None,
                    )
                    return (item.tweet_id, saved_location)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error(
                            f"Failed to download {item.media_url} after {max_retries} retries: {e}"
                        )
                        return (item.tweet_id, None)
                    logger.warning(
                        f"Error downloading {item.media_url} (attempt {retry_count}/{max_retries}): {e}"
                    )
                    await asyncio.sleep(retry_delay * retry_count)

            return (item.tweet_id, None)

        results = await tqdm_asyncio.gather(
            *(_download_single(item) for item in media_list.media),
            desc=progress_desc,
        )

    download_results: Dict[str, List[MediaLocation]] = {}
    for tweet_id, location in results:
        if location:
            if tweet_id not in download_results:
                download_results[tweet_id] = []
            download_results[tweet_id].append(location)

    return download_results
