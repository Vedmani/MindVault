"""Playwright-based Twitter scraping functionality for the MindVault application.

This module handles scraping tweets using Playwright to intercept Twitter's GraphQL API calls.
"""

import time
from pathlib import Path
from typing import List
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_chain,
    wait_fixed,
)
from tqdm import tqdm
from playwright.sync_api import sync_playwright, Error, Response

from mindvault.core.config import settings
from mindvault.core.logger_setup import get_logger, logger as base_logger
from mindvault.bookmarks.twitter.scraper.base import BaseTweetScraper, TweetNotFoundError

logger = get_logger(__name__)


class PlaywrightScraper(BaseTweetScraper):
    """Handles scraping tweet data from Twitter using Playwright.
    
    This class manages connecting to a Chrome instance, navigating to tweets,
    and intercepting GraphQL API responses to capture tweet data.
    
    Attributes:
        chrome_debug_port: Port for Chrome debugging connection
        captured_data: List to store intercepted tweet data
        initial_load_complete: Flag for first TweetDetail response
        next_response_received: Flag for subsequent responses after scrolling
    """

    def __init__(
        self,
        input_file: Path,
        chrome_debug_port: int = 9223,
        **kwargs
    ) -> None:
        """Initialize the Playwright scraper.
        
        Args:
            input_file: Path to JSON file containing tweet IDs
            chrome_debug_port: Port for Chrome debugging connection
        """
        super().__init__(input_file)
        self.chrome_debug_port = chrome_debug_port
        self.captured_data = []
        self.initial_load_complete = False
        self.next_response_received = False

    def format_output_json(self, data: List[dict]) -> dict:
        """Format multiple tweet responses into a single structured response.
        
        Args:
            data: List of tweet response dictionaries
            
        Returns:
            Formatted JSON structure containing all tweet data
        """
        out = {"threaded_conversation_with_injections_v2": {
            "instructions": [{"type": "TimelineAddEntries", "entries": []}]
        }}
        for item in data:
            # Follow the same pattern as the experimental script
            if "data" in item and "threaded_conversation_with_injections_v2" in item["data"]:
                instructions = item["data"]["threaded_conversation_with_injections_v2"]["instructions"]
                if instructions:
                    # Iterate through all instructions to find TimelineAddEntries
                    for instruction in instructions:
                        if (instruction.get("type") == "TimelineAddEntries" and 
                            "entries" in instruction):
                            out["threaded_conversation_with_injections_v2"]["instructions"][0]["entries"].extend(
                                instruction["entries"]
                            )
        return out

    def handle_response(self, response: Response) -> None:
        """Callback function to handle network responses, capturing raw TweetDetail JSON.
        
        Args:
            response: Playwright Response object
        """
        # Check if the URL matches the pattern for TweetDetail GraphQL API
        if "/i/api/graphql/" in response.url and "/TweetDetail" in response.url:
            try:
                data = response.json()
                logger.debug("TweetDetail response JSON successfully parsed")
                self.captured_data.append(data)

                # Signal that a response was received for pagination control
                if not self.initial_load_complete:
                    logger.info("Initial TweetDetail load complete")
                    self.initial_load_complete = True
                    self.next_response_received = True
                else:
                    logger.debug("Subsequent TweetDetail response received")
                    self.next_response_received = True

            except Exception as e:
                logger.error(f"Error processing TweetDetail response: {e}")
                try:
                    # Print text if JSON parsing fails
                    logger.debug(f"Response Text (first 500 chars): {response.text()[:500]}...")
                except Exception as text_e:
                    logger.error(f"Error getting response text: {text_e}")

    @retry(
        retry=retry_if_not_exception_type(TweetNotFoundError),
        wait=wait_chain(
            wait_fixed(5),   # First retry after 5s
            wait_fixed(15),  # Second retry after 15s
            wait_fixed(60),  # Third retry after 60s
        ),
        stop=stop_after_attempt(4),
        reraise=True,
        before_sleep=before_sleep_log(base_logger, "INFO"),
    )
    def get_tweet_data(self, tweet_id: int) -> dict:
        """Get tweet data for a single tweet ID using Playwright.
        
        Args:
            tweet_id: ID of the tweet to fetch
            
        Returns:
            Dictionary containing tweet data
            
        Raises:
            TweetNotFoundError: If tweet doesn't exist or is deleted
        """
        # Reset state for each tweet
        self.captured_data = []
        self.initial_load_complete = False
        self.next_response_received = False

        with sync_playwright() as playwright:
            try:
                # Connect to the existing Chrome instance via the debugging port
                browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{self.chrome_debug_port}")
                logger.debug(f"Successfully connected to Chrome over CDP on port {self.chrome_debug_port}")

                # Get the default context or create a new one if needed
                if not browser.contexts:
                    logger.warning("No browser contexts found. Creating a new context")
                    context = browser.new_context()
                    logger.debug("Created a new browser context")
                else:
                    context = browser.contexts[0]
                    logger.debug("Using existing browser context")

                # Create a new page within this context
                page = context.new_page()
                logger.debug("Created a new page in the browser context")

                # Set the color scheme to no-preference to respect the browser's theme
                page.emulate_media(color_scheme="no-preference")

                # Set up response handler BEFORE navigation
                page.on("response", self.handle_response)

                # Navigate to the Tweet
                tweet_url = f"https://x.com/i/status/{tweet_id}"
                logger.info(f"Navigating to tweet {tweet_id}")
                
                try:
                    page.goto(tweet_url, timeout=30000)
                    logger.debug(f"Navigation to {page.title()} complete")
                except Exception as nav_error:
                    logger.error(f"Navigation failed: {nav_error}")
                    page.close()
                    raise TweetNotFoundError(str(tweet_id), "Failed to navigate to tweet")

                # Wait for the initial TweetDetail response
                logger.debug("Waiting for the initial TweetDetail response...")
                wait_start_time = time.time()
                initial_wait_timeout = 30
                while not self.initial_load_complete:
                    page.wait_for_timeout(100)
                    if time.time() - wait_start_time > initial_wait_timeout:
                        logger.error(f"Timeout ({initial_wait_timeout}s) waiting for initial TweetDetail response")
                        page.close()
                        raise TweetNotFoundError(str(tweet_id), "Timeout waiting for tweet data")

                logger.debug("Initial TweetDetail response received. Starting pagination")

                # Implement Pagination through Scrolling to get full thread
                max_scrolls = 3
                scroll_count = 0
                stalled_scrolls = 0

                while scroll_count < max_scrolls:
                    scroll_count += 1
                    logger.debug(f"Performing scroll {scroll_count}/{max_scrolls}")

                    self.next_response_received = False
                    data_count_before_scroll = len(self.captured_data)

                    # Scroll to the bottom of the page
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                    # Wait for the next TweetDetail response after scrolling
                    wait_start_time = time.time()
                    scroll_wait_timeout = 5
                    while not self.next_response_received:
                        page.wait_for_timeout(100)
                        if time.time() - wait_start_time > scroll_wait_timeout:
                            logger.debug(f"Timeout waiting for TweetDetail response after scroll {scroll_count}")
                            break

                    # Add a small delay for rendering
                    if self.next_response_received:
                        page.wait_for_timeout(1000)

                    # Check if new data was captured
                    new_data_count = len(self.captured_data) - data_count_before_scroll
                    if new_data_count > 0:
                        logger.debug(f"Scroll {scroll_count} successful: Captured {new_data_count} new responses")
                        stalled_scrolls = 0
                    else:
                        logger.debug(f"No new responses captured after scroll {scroll_count}")
                        stalled_scrolls += 1
                        if stalled_scrolls >= 2:
                            logger.debug("Reached end of content (2 consecutive empty scrolls)")
                            break

                # Clean up
                page.remove_listener("response", self.handle_response)
                page.close()

                if not self.captured_data:
                    raise TweetNotFoundError(str(tweet_id), "No tweet data captured")

                # Format and return the captured data
                formatted_data = self.format_output_json(self.captured_data)
                logger.info(f"Successfully captured tweet data for {tweet_id}")
                return formatted_data

            except Error as playwright_error:
                logger.error(f"Playwright error occurred: {playwright_error}")
                raise TweetNotFoundError(str(tweet_id), f"Playwright error: {playwright_error}")
            except Exception as e:
                logger.error(f"Unexpected error occurred: {e}")
                if "No tweet data captured" in str(e) or isinstance(e, TweetNotFoundError):
                    raise
                raise TweetNotFoundError(str(tweet_id), f"Unexpected error: {e}")

    def scrape_tweets(self, max_consecutive_failures: int = 50) -> None:
        """Main method to scrape tweets using Playwright.
        
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
                        logger.error(f"Stopping: {max_consecutive_failures} consecutive failures reached")
                        break

        # Final statistics
        logger.info("Processing complete!")
        logger.info(f"Total tweets processed: {stats['processed']}/{total_tweets}")
        logger.info(f"Failed tweets: {stats['failed']}")


def main() -> None:
    """Main entry point for the Playwright tweet scraper."""
    scraper = PlaywrightScraper(
        input_file=settings.tweet_ids_path / "pending_tweets.json",
    )
    scraper.scrape_tweets()


if __name__ == "__main__":
    main()
