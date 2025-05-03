"""Workflow orchestration for the MindVault Twitter application.

This module automates the process of exporting bookmarks, finding pending tweets,
and scraping tweet data.
"""

import json
from pathlib import Path
from typing import Set, List
import asyncio

from mindvault.bookmarks.twitter.bookmarks import BookmarksExporter
from mindvault.core.config import settings
from mindvault.bookmarks.twitter.database import create_database, save_tweet_to_db, get_tweet_by_id
from mindvault.core.logger_setup import get_logger
from mindvault.bookmarks.twitter.pending import PendingTweetsFinder
from mindvault.bookmarks.twitter.scraper.cookie_scraper import CookieTweetScraper
from mindvault.bookmarks.twitter.schema import TweetData
from mindvault.bookmarks.twitter.extract import (
    extract_conversation_with_media,
    MediaUrlHandling,
    ExtractedConversationWithMedia,
    ExtractedMediaList,
    ExtractedMedia
)
from mindvault.bookmarks.twitter.download_tweet_media import download_tweet_media
from mindvault.core.mongodb_utils import save_extracted_tweet, get_extracted_media_for_tweets

logger = get_logger(__name__)

class WorkflowManager:
    """Manages the entire workflow of the MindVault Twitter application.
    
    This class orchestrates the process of exporting bookmarks, finding pending tweets,
    and scraping tweet data while maintaining state for recovery.
    
    Attributes:
        state_file: Path to the file storing workflow state
        use_existing_pending: Whether to use existing pending tweets file
    """
    
    def __init__(self, use_existing_pending: bool = False) -> None:
        """Initialize the workflow manager.
        
        Args:
            use_existing_pending: If True, uses existing pending_tweets.json instead of finding pending tweets
        """
        self.state_file = Path("workflow_state.json")
        self.use_existing_pending = use_existing_pending
        self.processed_tweets = []  # Track tweets processed in current run
        settings.setup_directories()
        create_database()

    def save_state(self, current_state: dict) -> None:
        """Save workflow state to file.
        
        Args:
            current_state: Dictionary containing current workflow state
        """
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(current_state, f, indent=2)

    def load_state(self) -> dict:
        """Load workflow state from file.
        
        Returns:
            Dictionary containing saved workflow state
        """
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def export_bookmarks(self) -> Path:
        """Export bookmarks and save tweet IDs.
        
        Returns:
            Path to the saved tweet IDs file
        """
        logger.info("Starting bookmarks export")
        exporter = BookmarksExporter()
        
        bookmarks = exporter.export_bookmarks()
        bookmarks_file = exporter.save_bookmarks(bookmarks)
        logger.info(f"Saved bookmarks to: {bookmarks_file}")
        
        tweet_ids = exporter.extract_tweet_ids(bookmarks)
        tweet_ids_file = exporter.save_tweet_ids(tweet_ids)
        logger.info(f"Saved {len(tweet_ids)} tweet IDs to: {tweet_ids_file}")
        
        return tweet_ids_file

    def load_pending_tweets(self) -> Set[str]:
        """Load pending tweets from the existing file.
        
        Returns:
            Set of pending tweet IDs
            
        Raises:
            FileNotFoundError: If pending tweets file doesn't exist
            JSONDecodeError: If file is not valid JSON
        """
        logger.info(f"Loading pending tweets from {settings.pending_tweets_path}")
        with open(settings.pending_tweets_path, 'r', encoding='utf-8') as f:
            return set(json.load(f))

    def find_pending_tweets(self, tweet_ids_file: Path) -> Set[str]:
        """Find tweets that haven't been processed yet.
        
        Args:
            tweet_ids_file: Path to file containing tweet IDs
            
        Returns:
            Set of pending tweet IDs
        """
        logger.info("Finding pending tweets")
        finder = PendingTweetsFinder(tweet_ids_file)
        stats = finder.get_stats()
        
        logger.info(f"Total tweets: {stats['total_tweets']}")
        logger.info(f"Processed tweets: {stats['processed_tweets']}")
        logger.info(f"Pending tweets: {stats['pending_tweets']}")
        
        return finder.find_pending_tweets()

    def extract_and_save_tweet_data(self, tweet_id: str, tweet_data: dict) -> None:
        """Extract and save valuable data from tweet.
        
        Args:
            tweet_id: ID of the tweet
            tweet_data: Raw tweet data dictionary
        """
        try:
            # Parse the tweet data
            tweet_data_model = TweetData.model_validate(tweet_data)
            
            # Extract conversation with media
            extracted_data = extract_conversation_with_media(
                tweet_data_model.threaded_conversation_with_injections_v2,
                media_url_handling=MediaUrlHandling.REMOVE,
                extract_video_thumbnail=False,
                extract_videos=True,
                extract_images=True,
                extract_card_images=True,
                video_length_limit=None  # No limit on video length
            )
            
            # Save extracted data to MongoDB
            save_extracted_tweet(tweet_id, extracted_data.model_dump())
            logger.info(f"Saved extracted data to MongoDB for tweet {tweet_id}")
            
        except Exception as e:
            logger.error(f"Error extracting data from tweet {tweet_id}: {e}")

    def scrape_tweets(self, pending_ids: Set[str], resume_from: str = None) -> List[str]:
        """Scrape pending tweets and save them to database.
        
        Args:
            pending_ids: Set of tweet IDs to scrape
            resume_from: Optional tweet ID to resume from
            
        Returns:
            List of tweet IDs that were successfully processed in this run
        """
        logger.info("Starting tweet scraping")
        
        # Reset processed tweets list for this run
        self.processed_tweets = []
        
        # Convert pending_ids to list and sort for consistent ordering
        pending_list = sorted(list(pending_ids))
        
        # Find start index if resuming
        start_idx = 0
        if resume_from:
            try:
                start_idx = pending_list.index(resume_from)
                logger.info(f"Resuming from tweet ID: {resume_from}")
            except ValueError:
                logger.warning(f"Resume point {resume_from} not found, starting from beginning")
        
        # Create temporary file for scraper
        temp_ids_file = Path("temp_pending_ids.json")
        with open(temp_ids_file, 'w', encoding='utf-8') as f:
            json.dump(pending_list[start_idx:], f)
        
        try:
            scraper = CookieTweetScraper(
                input_file=temp_ids_file,
            )
            
            for tweet_id in pending_list[start_idx:]:
                try:
                    # Skip if already in database
                    if get_tweet_by_id(tweet_id):
                        logger.info(f"Tweet {tweet_id} already processed, skipping")
                        continue
                    
                    # Get and save tweet data
                    tweet_data = scraper.get_tweet_data(int(tweet_id))
                    scraper.save_tweet_data(tweet_data, tweet_id)
                    
                    # Extract and save valuable data
                    self.extract_and_save_tweet_data(tweet_id, tweet_data)
                    
                    # Save tweet id to sqlite database
                    save_tweet_to_db(tweet_id)
                    
                    # Track processed tweet for this run
                    self.processed_tweets.append(tweet_id)
                    
                    # Update state after each successful tweet
                    self.save_state({"last_processed_id": tweet_id})
                    logger.info(f"Successfully processed tweet {tweet_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing tweet {tweet_id}: {e}")
                    # Continue with next tweet
                    continue
                    
        finally:
            # Clean up temporary file
            temp_ids_file.unlink(missing_ok=True)
            
        return self.processed_tweets
    
    def download_media_for_tweets(self, tweet_ids: List[str], max_connections: int = 50) -> None:
        """Download media only for specified tweets.
        
        Args:
            tweet_ids: List of tweet IDs to download media for
            max_connections: Maximum number of concurrent connections for downloading
        """
        if not tweet_ids:
            logger.info("No tweets to download media for")
            return
            
        logger.info(f"Starting media download for {len(tweet_ids)} tweets from current run")
        
        try:
            # Get media information from MongoDB
            all_media = get_extracted_media_for_tweets(tweet_ids)
            
            if not all_media:
                logger.info("No media found in the specified tweets")
                return
                
            logger.info(f"Found {len(all_media)} media items to download")
            
            # Download media
            asyncio.run(
                download_tweet_media(
                    output_dir=settings.media_dir,
                    media_list=ExtractedMediaList(media=all_media),
                    max_connections=max_connections
                )
            )
            
            logger.info("Media download completed for current run")
            
        except Exception as e:
            logger.error(f"Error downloading media for tweets: {e}")
            raise

    def run(self) -> None:
        """Run the complete workflow."""
        try:
            # Check for existing state
            state = self.load_state()
            resume_from = state.get("last_processed_id")
            
            # Get pending tweets
            if self.use_existing_pending:
                try:
                    pending_ids = self.load_pending_tweets()
                    logger.info(f"Loaded {len(pending_ids)} pending tweets from existing file")
                except FileNotFoundError:
                    logger.error(f"Pending tweets file not found at {settings.pending_tweets_path}")
                    logger.info("Falling back to finding pending tweets")
                    self.use_existing_pending = False
            
            if not self.use_existing_pending:
                # Export bookmarks and get tweet IDs
                tweet_ids_file = self.export_bookmarks()
                # Find pending tweets
                pending_ids = self.find_pending_tweets(tweet_ids_file)
            
            if not pending_ids:
                logger.info("No pending tweets to process")
                return
            
            # Scrape pending tweets and get IDs of processed tweets
            processed_tweets = self.scrape_tweets(pending_ids, resume_from)
            
            # Download media only for tweets processed in this run
            self.download_media_for_tweets(processed_tweets)
            
            logger.info("Workflow completed successfully")
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise


def main(use_existing_pending: bool = False) -> None:
    """Main entry point for the workflow.
    
    Args:
        use_existing_pending: If True, uses existing pending_tweets.json instead of finding pending tweets
    """
    workflow = WorkflowManager(use_existing_pending)
    workflow.run()


if __name__ == "__main__":
    # import argparse
    
    # parser = argparse.ArgumentParser(description="Run the MindVault Twitter workflow")
    # parser.add_argument(
    #     "--use-existing-pending",
    #     action="store_true",
    #     help="Use existing pending_tweets.json instead of finding pending tweets"
    # )
    
    # args = parser.parse_args()
    # main(use_existing_pending = True) 
    main(use_existing_pending=False)