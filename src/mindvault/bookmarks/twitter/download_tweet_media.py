"""
Module for downloading media from Twitter tweets based on media information extracted from tweets.
"""

import asyncio
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Generator
from urllib.parse import urlsplit
import functools

import aiofiles
import httpx
from httpx import AsyncClient, Limits
from tqdm.asyncio import tqdm_asyncio

from mindvault.bookmarks.twitter.extract import (
    ExtractedMediaList,
    ExtractedMedia,
    extract_media_info_from_conversation
)
from mindvault.core.config import settings
from mindvault.core.logger_setup import logger

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

# Default configuration
DEFAULT_CONFIG = {
    "chunk_size": 8192,
    "max_connections": 50,
    "max_keepalive_connections": None,
    "keepalive_expiry": 5.0,
    "max_retries": 3,
    "retry_delay": 1.0,
    "timeout": 60,
    "skip_existing": True,
}


async def _create_http_client(
    max_connections: int = 50, 
    max_keepalive_connections: Optional[int] = None,
    keepalive_expiry: float = 5.0,
    timeout: int = 60,
    user_agent: Optional[str] = None
) -> AsyncClient:
    """
    Create an HTTP client for downloading media.

    Args:
        max_connections: Maximum number of concurrent connections
        max_keepalive_connections: Maximum number of connections to keep alive (defaults to max_connections if None)
        keepalive_expiry: Time in seconds to keep a connection alive
        timeout: Timeout for HTTP requests in seconds
        user_agent: User agent string to use, if None a random one is chosen

    Returns:
        AsyncClient instance
    """
    # If max_keepalive_connections is not set, use max_connections
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
        follow_redirects=True
    )


def get_file_path(item: ExtractedMedia, base_dir: Path) -> Path:
    """
    Get the file path for a media item.

    Args:
        item: DownloadMedia object
        base_dir: Base directory for downloads

    Returns:
        Path object for the file
    """
    url = item.media_url
    ext = urlsplit(url).path.split("/")[-1].split("?")[0]  # Remove query params from extension
    
    # Create a subdirectory for each tweet_id
    tweet_dir = base_dir / item.tweet_id
    tweet_dir.mkdir(exist_ok=True, parents=True)
    
    # Create filename using media_id
    filename = f"{item.media_id}"
    if "." not in filename and "." in ext:
        filename = f"{filename}.{ext.split('.')[-1]}"
    
    return tweet_dir / filename


async def _download_single_file(
    client: AsyncClient, 
    item: ExtractedMedia,
    out_path: Path,
    chunk_size: int = 32768,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    skip_existing: bool = True
) -> Tuple[str, Path]:
    """
    Download a single media file with retry logic.

    Args:
        client: AsyncClient instance
        item: DownloadMedia object
        out_path: Base output directory
        chunk_size: Size of chunks when downloading files
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        skip_existing: Skip download if file already exists

    Returns:
        Tuple of (tweet_id, file_path)
    """
    file_path = get_file_path(item, out_path)
    
    # Skip if file already exists and skip_existing is True
    if skip_existing and file_path.exists() and file_path.stat().st_size > 0:
        logger.debug(f"File already exists, skipping: {file_path}")
        return (item.tweet_id, file_path)
    
    url = item.media_url
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            async with aiofiles.open(file_path, "wb") as fp:
                async with client.stream("GET", url) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_raw(chunk_size):
                        await fp.write(chunk)
            return (item.tweet_id, file_path)
        
        except (httpx.HTTPError, IOError) as e:
            retry_count += 1
            if retry_count > max_retries:
                logger.error(f"Failed to download {url} after {max_retries} retries: {e}")
                return (item.tweet_id, None)
            
            logger.warning(f"Error downloading {url} (attempt {retry_count}/{max_retries}): {e}")
            await asyncio.sleep(retry_delay * retry_count)  # Exponential backoff
    
    return (item.tweet_id, None)



async def download_tweet_media(
    media_list: ExtractedMediaList,
    output_dir: Optional[Union[str, Path]] = None,
    **kwargs
) -> Dict[str, List[Path]]:
    """
    Download media from Twitter tweets.

    Args:
        media_list: DownloadedMediaList from extract_media_info_from_conversation
        output_dir: Directory to save downloaded media (defaults to settings.media_dir)
        **kwargs: Additional keyword arguments
            - chunk_size: Size of chunks when downloading files (default: 8192)
            - max_connections: Maximum number of concurrent connections (default: 50)
            - max_keepalive_connections: Maximum number of connections to keep alive
            - keepalive_expiry: Time in seconds to keep a connection alive (default: 5.0)
            - max_retries: Maximum number of retry attempts (default: 3)
            - retry_delay: Delay between retries in seconds (default: 1.0)
            - timeout: Timeout for HTTP requests in seconds (default: 60)
            - skip_existing: Skip download if file already exists (default: True)

    Returns:
        Dictionary mapping tweet IDs to lists of downloaded file paths
    """
    if not media_list.media:
        logger.warning("No media items to download")
        return {}
    
    # Use settings.media_dir as default and ensure Path object
    if output_dir is None:
        out_path = Path(settings.media_dir)
    else:
        out_path = Path(output_dir)
    
    # Create output directory
    out_path.mkdir(parents=True, exist_ok=True)
    
    def generate_download_tasks(media_items, out_dir: Path) -> Generator:
        """Generate download tasks as a generator of partial functions"""
        for item in media_items:
            yield functools.partial(
                _download_single_file,
                item=item,
                out_path=out_dir,
                chunk_size=kwargs.get("chunk_size", 32768),
                max_retries=kwargs.get("max_retries", 3),
                retry_delay=kwargs.get("retry_delay", 1.0),
                skip_existing=kwargs.get("skip_existing", True)
            )
    
    # Create HTTP client with default or user-provided settings
    async with await _create_http_client(
        max_connections=kwargs.get("max_connections", 50),
        max_keepalive_connections=kwargs.get("max_keepalive_connections"),
        keepalive_expiry=kwargs.get("keepalive_expiry", 5.0),
        timeout=kwargs.get("timeout", 60)
    ) as client:
        # Execute tasks concurrently with progress bar using generator approach
        results = await tqdm_asyncio.gather(
            *(fn(client=client) for fn in generate_download_tasks(media_list.media, out_path)),
            desc=f"Downloading {len(media_list.media)} media files"
        )
    
    # Organize results by tweet_id
    download_results = {}
    for tweet_id, file_path in results:
        if file_path:  # Only include successful downloads
            if tweet_id not in download_results:
                download_results[tweet_id] = []
            download_results[tweet_id].append(file_path)
    
    return download_results


if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    from mindvault.bookmarks.twitter.extract import (
        process_single_tweet_file,
        extract_media_info_from_conversation,
    )

    async def main():
        # Example usage for a single conversation
        tweet_file = Path("artifacts/tweet_data/1895195365269467454.json")
        tweet_file_2 = Path("artifacts/tweet_data/1894346156656005380.json")
        # Method 1: Step by step with default output directory (settings.media_dir)
        conversation = process_single_tweet_file(tweet_file)
        conversation_2 = process_single_tweet_file(tweet_file_2)
        
        if conversation:
            # Extract media info
            media_list = extract_media_info_from_conversation(conversation, extract_card_images=False)
            media_list_2 = extract_media_info_from_conversation(conversation_2, extract_card_images=False)
            media_list.media.extend(media_list_2.media)
            # Download media to the default directory
            results = await download_tweet_media(
                output_dir="media",
                media_list=media_list,
                max_connections=50
            )
            print(f"Downloaded media: {results}")
    
    # Run the async main function
    asyncio.run(main())
