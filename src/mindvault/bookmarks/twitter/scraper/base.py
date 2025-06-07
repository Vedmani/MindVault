"""Twitter scraping functionality for the MindVault application.

This module handles scraping tweets using the Twitter API.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from tqdm import tqdm

from mindvault.core.config import settings
from mindvault.core.logger_setup import get_logger, logger as base_logger
from mindvault.core.mongodb_utils import save_raw_tweet

logger = get_logger(__name__)

class TweetNotFoundError(Exception):
    """Raised when a tweet cannot be found or has been deleted.
    
    Attributes:
        tweet_id: ID of the tweet that wasn't found
        message: Error message with details
    """

    def __init__(self, tweet_id: str, message: str = "Tweet not found or deleted") -> None:
        self.tweet_id = tweet_id
        self.message = f"{message} (Tweet ID: {tweet_id})"
        super().__init__(self.message)


class BaseTweetScraper(ABC):
    """Base class for scraping tweets using the Twitter API.
    
    This abstract base class defines the interface that all tweet scrapers must implement.
    """

    def __init__(self, input_file: Path, **kwargs) -> None:
        """Initialize the base scraper.
        
        Args:
            input_file: Path to JSON file containing tweet IDs
            **kwargs: Additional arguments for specific scraper implementations
        """
        self.input_file = Path(input_file)

    def load_tweet_ids(self) -> List[int]:
        """Load tweet IDs from the input file.
        
        Returns:
            List of tweet IDs as integers
            
        Raises:
            Exception: If loading tweet IDs fails
        """
        try:
            tweet_ids = json.loads(self.input_file.read_text())
            return [int(tweet_id) for tweet_id in tweet_ids]
        except Exception as e:
            logger.error(f"Failed to load tweet IDs: {e}")
            raise

    def save_tweet_data(self, tweet_data: dict, tweet_id: str) -> None:
        """Save tweet data to MongoDB.
        
        Args:
            tweet_data: Dictionary containing tweet data
            tweet_id: ID of the tweet
            
        Raises:
            Exception: If saving tweet data fails
        """
        try:
            save_raw_tweet(tweet_id, tweet_data)
        except Exception as e:
            logger.error(f"Failed to save tweet data for ID {tweet_id}: {e}")
            raise

    @abstractmethod
    def get_tweet_data(self, tweet_id: int) -> dict:
        """Get tweet data for a single tweet ID.
        
        Args:
            tweet_id: ID of the tweet to fetch
            
        Returns:
            Dictionary containing tweet data
            
        Raises:
            TweetNotFoundError: If tweet doesn't exist or is deleted
        """
        pass

    @abstractmethod
    def scrape_tweets(self, max_consecutive_failures: int = 50) -> None:
        """Main method to scrape tweets.
        
        Args:
            max_consecutive_failures: Maximum number of consecutive failures before stopping
        """
        pass
