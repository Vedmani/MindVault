"""
Deprecated compatibility wrapper for RustFS-specific media uploads.
"""

import warnings
from typing import Dict, List, Optional

from mindvault.bookmarks.twitter.download_tweet_media_object_storage import (
    download_tweet_media_to_blob_storage,
)
from mindvault.bookmarks.twitter.extract import ExtractedMediaList


async def download_tweet_media_to_rustfs(
    media_list: ExtractedMediaList,
    bucket_name: Optional[str] = None,
    **kwargs,
) -> Dict[str, List[str]]:
    """
    Deprecated wrapper around `download_tweet_media_to_blob_storage`.
    """
    warnings.warn(
        (
            "`download_tweet_media_to_rustfs` is deprecated and will be removed in a "
            "future release. Use `download_tweet_media_to_blob_storage(..., provider=\"rustfs\")`."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    return await download_tweet_media_to_blob_storage(
        media_list=media_list,
        provider="rustfs",
        bucket_name=bucket_name,
        **kwargs,
    )
