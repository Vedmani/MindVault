"""
Module for downloading media from Twitter tweets based on media information extracted from tweets.
"""

import asyncio
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional, Union

import aiofiles

from mindvault.bookmarks.twitter.extract import (
    ExtractedMediaList,
    ExtractedMedia,
    extract_media_info_from_conversation,
)
from mindvault.bookmarks.twitter.media_download import (
    build_media_key,
    download_media,
)
from mindvault.core.config import settings


class FileSystemMediaStore:
    """Filesystem-backed media storage."""

    def __init__(self, base_dir: Union[str, Path]) -> None:
        self.base_dir = Path(base_dir)

    async def prepare(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_location(self, item: ExtractedMedia) -> Path:
        return self.base_dir / build_media_key(item)

    async def exists(self, item: ExtractedMedia) -> bool:
        file_path = self.get_location(item)
        return file_path.exists() and file_path.stat().st_size > 0

    async def save(
        self,
        item: ExtractedMedia,
        stream: AsyncIterator[bytes],
        *,
        content_type: Optional[str] = None,
    ) -> Path:
        file_path = self.get_location(item)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with aiofiles.open(file_path, "wb") as fp:
                async for chunk in stream:
                    await fp.write(chunk)

            if file_path.exists() and file_path.stat().st_size == 0:
                file_path.unlink(missing_ok=True)
                raise IOError(f"Empty file received for {file_path}")

            return file_path
        except Exception:
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise


async def download_tweet_media(
    media_list: ExtractedMediaList,
    output_dir: Optional[Union[str, Path]] = None,
    **kwargs,
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
    out_path = Path(settings.media_dir) if output_dir is None else Path(output_dir)
    store = FileSystemMediaStore(out_path)

    results = await download_media(
        media_list=media_list,
        store=store,
        progress_desc=f"Downloading {len(media_list.media)} media files",
        **kwargs,
    )

    return results


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
                max_connections=50,
            )
            print(f"Downloaded media: {results}")

    # Run the async main function
    asyncio.run(main())
