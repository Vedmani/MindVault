"""Twitter scraping functionality for the MindVault application.

This module handles scraping tweets using the Twitter API.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_chain,
    wait_fixed,
)
from tqdm import tqdm
from twitter.scraper import Scraper as TwitterScraper

from mindvault.core.config import settings
from mindvault.core.logger_setup import get_logger, logger as base_logger
from mindvault.core.mongodb_utils import save_raw_tweet
from mindvault.bookmarks.twitter.scraper.base import BaseTweetScraper, TweetNotFoundError

logger = get_logger(__name__)


class CookieTweetScraper(BaseTweetScraper):
    """Handles scraping tweet data from Twitter.
    
    This class manages loading tweet IDs, fetching tweet data, and saving it to MongoDB.
    
    Attributes:
        input_file: Path to JSON file containing tweet IDs
        auth: Authentication details for Twitter API
        scraper: Instance of Twitter scraper
    """

    def __init__(
        self,
        input_file: Path,
        auth_details: Optional[Dict[str, str]] = None
    ) -> None:
        """Initialize the tweet scraper.
        
        Args:
            input_file: Path to JSON file containing tweet IDs
            auth_details: Optional auth details dict. If None, uses default auth
        """
        super().__init__(input_file)
        self.auth = auth_details or settings.get_scraper_auth()
        self.scraper = TwitterScraper(cookies=self.auth, pbar=False, save=False)



    @retry(
        retry=retry_if_not_exception_type(TweetNotFoundError),
        wait=wait_chain(
            wait_fixed(5),   # First retry after 5s
            wait_fixed(15),  # Second retry after 15s
            wait_fixed(960), # Third retry after 16min
        ),
        stop=stop_after_attempt(4),
        reraise=True,
        before_sleep=before_sleep_log(base_logger, "INFO"),
    )
    def get_tweet_data(self, tweet_id: int) -> dict:
        """Get tweet data for a single tweet ID with retries.
        
        Args:
            tweet_id: ID of the tweet to fetch
            
        Returns:
            Dictionary containing tweet data
            
        Raises:
            TweetNotFoundError: If tweet doesn't exist or is deleted
        """
        tweet = self.scraper.tweets_details([tweet_id])
        if "errors" in tweet[0]:
            raise TweetNotFoundError(str(tweet_id))
        return tweet[0]["data"]

    def scrape_tweets(self, max_consecutive_failures: int = 50) -> None:
        """Main method to scrape tweets.
        
        Args:
            max_consecutive_failures: Maximum number of consecutive failures before stopping
        """
        tweet_ids = self.load_tweet_ids()
        total_tweets = len(tweet_ids)
        logger.info(f"Total tweets to process: {total_tweets}")

        stats = {
            "processed": 0,
            "failed": 0,
            "consecutive_failures": 0
        }

        with tqdm(
            total=total_tweets,
            desc="Processing tweets",
            unit="tweet",
            ncols=100,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
        ) as pbar:
            for tweet_id in tweet_ids:
                try:
                    tweet_data = self.get_tweet_data(tweet_id)
                    self.save_tweet_data(tweet_data, str(tweet_id))
                    
                    stats["consecutive_failures"] = 0
                    stats["processed"] += 1
                    pbar.update(1)
                    pbar.set_postfix(
                        failed=stats["failed"],
                        consecutive_fails=stats["consecutive_failures"]
                    )

                except Exception as e:
                    logger.error(f"Error processing tweet {tweet_id}: {e}")
                    stats["failed"] += 1
                    stats["consecutive_failures"] += 1
                    pbar.set_postfix(
                        failed=stats["failed"],
                        consecutive_fails=stats["consecutive_failures"]
                    )

                    if stats["consecutive_failures"] >= max_consecutive_failures:
                        logger.error(f"\nStopping: {max_consecutive_failures} consecutive failures reached")
                        break

        # Final statistics
        logger.info("\nProcessing complete!")
        logger.info(f"Total tweets processed: {stats['processed']}/{total_tweets}")
        logger.info(f"Failed tweets: {stats['failed']}")


def main() -> None:
    """Main entry point for the tweet scraper."""
    scraper = CookieTweetScraper(
        input_file=settings.tweet_ids_path / "pending_tweets.json",
    )
    scraper.scrape_tweets()


if __name__ == "__main__":
    main() 