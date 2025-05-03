"""Twitter bookmarks export functionality for the MindVault application.

This module handles exporting Twitter bookmarks and extracting tweet IDs.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from twitter.account import Account

from mindvault.core.config import settings
from mindvault.core.logger_setup import get_logger

logger = get_logger(__name__)

class BookmarksExporter:
    """Handles exporting Twitter bookmarks and extracting tweet IDs.
    
    This class manages authentication with Twitter and exports bookmarks data.
    
    Attributes:
        account: Authenticated Twitter account instance
    """
    
    def __init__(self) -> None:
        """Initialize the bookmarks exporter with Twitter authentication."""
        self.account = Account(
            cookies=settings.get_bookmarks_auth()
        )

    def export_bookmarks(self) -> List[Dict]:
        """Export bookmarks from Twitter account.
        
        Returns:
            List of bookmark data dictionaries
            
        Raises:
            Exception: If fetching bookmarks fails
        """
        logger.info("Exporting bookmarks from Twitter account")
        return self.account.bookmarks()

    def save_bookmarks(self, bookmarks: List[Dict]) -> Path:
        """Save bookmarks data to a JSON file.
        
        Args:
            bookmarks: List of bookmark data dictionaries
            
        Returns:
            Path to the saved bookmarks file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = settings.bookmarks_path / f"bookmarks_{timestamp}.json"
        
        logger.info(f"Saving {len(bookmarks)} bookmarks to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(bookmarks, f, ensure_ascii=False, indent=2)
            
        return filename

    def extract_tweet_ids(self, bookmarks: List[Dict]) -> List[str]:
        """Extract tweet IDs from bookmarks data.
        
        Args:
            bookmarks: List of bookmark data dictionaries
            
        Returns:
            List of tweet IDs
        """
        tweet_ids = []
        logger.info(f"Extracting tweet IDs from {len(bookmarks)} bookmarks")
        for bookmark in bookmarks:
            try:
                entries = bookmark["data"]["bookmark_timeline_v2"]["timeline"]["instructions"][0]["entries"]
                for entry in entries:
                    if "tweet" in entry["entryId"]:
                        tweet_id = entry["entryId"].split("-")[1]
                        tweet_ids.append(tweet_id)
            except Exception as e:
                logger.error(f"Error processing bookmark: {e}")
                continue
        logger.info(f"Successfully extracted {len(tweet_ids)} tweet IDs")
        return tweet_ids

    def save_tweet_ids(self, tweet_ids: List[str]) -> Path:
        """Save tweet IDs to a JSON file.
        
        Args:
            tweet_ids: List of tweet IDs
            
        Returns:
            Path to the saved tweet IDs file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = settings.tweet_ids_path / f"tweets_ids_{timestamp}.json"
        
        logger.info(f"Saving {len(tweet_ids)} tweet IDs to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(tweet_ids, f, ensure_ascii=False, indent=2)
            
        return filename


def main() -> None:
    """Main entry point for the bookmarks export process."""
    logger.info("Starting bookmarks export process")
    settings.setup_directories()
    
    exporter = BookmarksExporter()
    bookmarks = exporter.export_bookmarks()
    bookmarks_file = exporter.save_bookmarks(bookmarks)
    logger.info(f"Saved bookmarks to: {bookmarks_file}")
    
    tweet_ids = exporter.extract_tweet_ids(bookmarks)
    tweet_ids_file = exporter.save_tweet_ids(tweet_ids)
    logger.info(f"Saved {len(tweet_ids)} tweet IDs to: {tweet_ids_file}")
    logger.info("Bookmarks export process completed")


if __name__ == "__main__":
    main() 