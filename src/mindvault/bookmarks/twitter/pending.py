"""Pending tweets finder for the MindVault application.

This module identifies tweets that haven't been processed yet.
"""

import json
from pathlib import Path
from typing import Set

from mindvault.bookmarks.twitter.database import get_existing_tweet_ids
from mindvault.core.config import settings
from mindvault.core.logger_setup import get_logger

logger = get_logger(__name__)

class PendingTweetsFinder:
    """Finds tweets that haven't been processed yet.
    
    This class compares tweet IDs from a source file against those in the database
    to identify pending tweets.
    
    Attributes:
        source_file: Path to JSON file containing all tweet IDs
    """
    
    def __init__(self, source_file: Path) -> None:
        """Initialize the pending tweets finder.
        
        Args:
            source_file: Path to JSON file containing all tweet IDs
        """
        self.source_file = Path(source_file)

    def load_source_tweet_ids(self) -> Set[str]:
        """Load tweet IDs from the source file.
        
        Returns:
            Set of tweet IDs from source file
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            JSONDecodeError: If source file is not valid JSON
        """
        logger.info(f"Loading tweet IDs from source file: {self.source_file}")
        with open(self.source_file, 'r', encoding='utf-8') as f:
            tweet_ids = set(json.load(f))
        logger.info(f"Loaded {len(tweet_ids)} tweet IDs from source file")
        return tweet_ids

    def find_pending_tweets(self) -> Set[str]:
        """Find tweets that haven't been processed yet.
        
        Returns:
            Set of pending tweet IDs
            
        Raises:
            Exception: If loading tweet IDs or querying database fails
        """
        logger.info("Finding pending tweets")
        source_ids = self.load_source_tweet_ids()
        logger.info("Getting processed tweet IDs from database")
        processed_ids = get_existing_tweet_ids()
        pending_ids = source_ids - processed_ids
        logger.info(f"Found {len(pending_ids)} pending tweets")
        return pending_ids

    def save_pending_tweets(self, pending_ids: Set[str], output_file: Path) -> None:
        """Save pending tweet IDs to a JSON file.
        
        Args:
            pending_ids: Set of pending tweet IDs
            output_file: Path to save the pending IDs
            
        Raises:
            IOError: If writing to output file fails
        """
        logger.info(f"Saving {len(pending_ids)} pending tweet IDs to {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(list(pending_ids), f, indent=2)
        logger.info("Successfully saved pending tweet IDs")

    def get_stats(self) -> dict:
        """Get statistics about pending tweets.
        
        Returns:
            Dictionary containing tweet statistics
        """
        logger.info("Calculating tweet statistics")
        source_ids = self.load_source_tweet_ids()
        processed_ids = get_existing_tweet_ids()
        pending_ids = source_ids - processed_ids
        
        stats = {
            "total_tweets": len(source_ids),
            "processed_tweets": len(processed_ids),
            "pending_tweets": len(pending_ids)
        }
        logger.debug(f"Tweet statistics: {stats}")
        return stats


def main() -> None:
    """Main entry point for finding pending tweets."""
    logger.info("Starting pending tweets finder")
    source_file = Path('artifacts/bookmark_ids/tweets_ids_20250829_192809.json')
    
    finder = PendingTweetsFinder(source_file)
    pending_ids = finder.find_pending_tweets()
    
    # Save pending tweets only when run as main
    finder.save_pending_tweets(pending_ids, settings.pending_tweets_path)
    
    stats = finder.get_stats()
    logger.info(f"Total tweets in source file: {stats['total_tweets']}")
    logger.info(f"Tweets in database: {stats['processed_tweets']}")
    logger.info(f"Pending tweets: {stats['pending_tweets']}")
    logger.info(f"Pending tweets saved to: {settings.pending_tweets_path}")
    logger.info("Pending tweets finder completed")


if __name__ == "__main__":
    main() 