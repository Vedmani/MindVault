# API Documentation

This document provides comprehensive API reference for MindVault's classes, functions, and modules.

## Core Modules

### Configuration (`mindvault.core.config`)

The configuration module manages all settings for MindVault.

#### Settings Class

```python
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `twitter_ct0` | `str` | Twitter ct0 cookie for authentication |
| `twitter_auth_token` | `str` | Twitter auth token for authentication |
| `twitter_scraper_ct0` | `str` | Optional separate ct0 for scraping |
| `twitter_scraper_auth_token` | `str` | Optional separate auth token |
| `base_dir` | `Path` | Base directory for data storage |
| `mongodb_uri` | `str` | MongoDB connection URI |
| `db_name` | `str` | Database name |

**Methods:**

```python
def get_bookmarks_auth() -> dict:
    """Get authentication details for bookmarks export."""
    
def get_scraper_auth() -> dict:
    """Get authentication details for tweet scraping."""
    
def validate_mongodb_connection() -> bool:
    """Validates the connection to MongoDB."""
```

**Example Usage:**

```python
from mindvault.core.config import settings

# Get authentication
auth = settings.get_bookmarks_auth()

# Validate MongoDB connection
if settings.validate_mongodb_connection():
    print("Database connection successful")
```

### MongoDB Utils (`mindvault.core.mongodb_utils`)

MongoDB utilities for database operations.

#### MongoDBUtils Class

```python
class MongoDBUtils:
    """MongoDB database utilities."""
```

**Methods:**

```python
def insert_document(collection_name: str, document: dict) -> str:
    """Insert a document into a collection."""
    
def query_collection(collection_name: str, query: dict) -> list:
    """Query documents from a collection."""
    
def update_document(collection_name: str, query: dict, update: dict) -> int:
    """Update documents in a collection."""
    
def delete_document(collection_name: str, query: dict) -> int:
    """Delete documents from a collection."""
    
def get_collection_stats(collection_name: str) -> dict:
    """Get statistics for a collection."""
```

**Example Usage:**

```python
from mindvault.core.mongodb_utils import MongoDBUtils

db = MongoDBUtils()

# Insert document
doc_id = db.insert_document("bookmarks", {
    "tweet_id": "123456789",
    "user_name": "example_user",
    "content": "Example tweet content"
})

# Query documents
results = db.query_collection("bookmarks", {
    "user_name": "example_user"
})
```

### Logger Setup (`mindvault.core.logger_setup`)

Logging configuration and utilities.

#### Functions

```python
def get_logger(name: str) -> Logger:
    """Get a configured logger instance."""
    
def setup_logging(level: str = "INFO", log_dir: str = None) -> None:
    """Set up logging configuration."""
```

**Example Usage:**

```python
from mindvault.core.logger_setup import get_logger

logger = get_logger(__name__)
logger.info("Application started")
logger.error("An error occurred")
```

## Twitter/X Integration

### Bookmarks Export (`mindvault.bookmarks.twitter.bookmarks`)

Handle Twitter bookmarks export functionality.

#### BookmarksExporter Class

```python
class BookmarksExporter:
    """Export Twitter bookmarks."""
```

**Methods:**

```python
def export_bookmarks(max_pages: int = None) -> list:
    """Export Twitter bookmarks."""
    
def save_bookmarks(bookmarks: list, filename: str = None) -> str:
    """Save bookmarks to file."""
    
def get_bookmark_count() -> int:
    """Get total number of bookmarks."""
```

**Example Usage:**

```python
from mindvault.bookmarks.twitter.bookmarks import BookmarksExporter

exporter = BookmarksExporter()
bookmarks = exporter.export_bookmarks(max_pages=10)
filename = exporter.save_bookmarks(bookmarks)
```

### Tweet Processing (`mindvault.bookmarks.twitter.extract`)

AI-powered tweet content extraction and analysis.

#### TweetExtractor Class

```python
class TweetExtractor:
    """Extract and analyze tweet content."""
```

**Methods:**

```python
def extract_tweet_data(tweet_id: str) -> dict:
    """Extract structured data from a tweet."""
    
def extract_entities(text: str) -> dict:
    """Extract entities from text."""
    
def analyze_sentiment(text: str) -> dict:
    """Analyze sentiment of text."""
    
def extract_topics(text: str) -> list:
    """Extract topics from text."""
```

**Example Usage:**

```python
from mindvault.bookmarks.twitter.extract import TweetExtractor

extractor = TweetExtractor()
analysis = extractor.extract_tweet_data("123456789")

print(f"Entities: {analysis['entities']}")
print(f"Topics: {analysis['topics']}")
print(f"Sentiment: {analysis['sentiment']}")
```

### Database Operations (`mindvault.bookmarks.twitter.database`)

Twitter-specific database operations.

#### BookmarkDB Class

```python
class BookmarkDB:
    """Database operations for Twitter bookmarks."""
```

**Methods:**

```python
def save_bookmark(bookmark: dict) -> str:
    """Save a bookmark to database."""
    
def get_bookmark(tweet_id: str) -> dict:
    """Get a bookmark by tweet ID."""
    
def get_all_bookmarks() -> list:
    """Get all bookmarks."""
    
def search_bookmarks(*keywords: str) -> list:
    """Search bookmarks by keywords."""
    
def get_bookmarks_by_user(username: str) -> list:
    """Get bookmarks by user."""
    
def get_bookmarks_by_date_range(start_date: str, end_date: str) -> list:
    """Get bookmarks within date range."""
```

**Example Usage:**

```python
from mindvault.bookmarks.twitter.database import BookmarkDB

db = BookmarkDB()

# Save bookmark
bookmark_id = db.save_bookmark({
    "tweet_id": "123456789",
    "user_name": "example_user",
    "content": "Example tweet",
    "created_at": "2024-01-01T12:00:00Z"
})

# Search bookmarks
results = db.search_bookmarks("AI", "machine learning")
```

### Media Download (`mindvault.bookmarks.twitter.download_tweet_media`)

Download and manage tweet media content.

#### TweetMediaDownloader Class

```python
class TweetMediaDownloader:
    """Download media from tweets."""
```

**Methods:**

```python
def download_tweet_media(tweet_id: str) -> list:
    """Download all media for a tweet."""
    
def download_image(url: str, filename: str) -> str:
    """Download an image from URL."""
    
def download_video(url: str, filename: str) -> str:
    """Download a video from URL."""
    
def get_media_info(tweet_id: str) -> dict:
    """Get media information for a tweet."""
```

**Example Usage:**

```python
from mindvault.bookmarks.twitter.download_tweet_media import TweetMediaDownloader

downloader = TweetMediaDownloader()
media_files = downloader.download_tweet_media("123456789")
print(f"Downloaded {len(media_files)} media files")
```

### Workflow Management (`mindvault.bookmarks.twitter.workflow`)

Orchestrate complex Twitter data processing workflows.

#### WorkflowManager Class

```python
class WorkflowManager:
    """Manage Twitter data processing workflows."""
```

**Methods:**

```python
def process_bookmarks(start_date: str = None, end_date: str = None) -> dict:
    """Process bookmarks workflow."""
    
def process_batch(batch_size: int = 100) -> dict:
    """Process tweets in batches."""
    
def schedule_workflow(workflow_name: str, interval: str) -> str:
    """Schedule a workflow to run automatically."""
```

**Example Usage:**

```python
from mindvault.bookmarks.twitter.workflow import WorkflowManager

workflow = WorkflowManager()
result = workflow.process_bookmarks(
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

## Browser Integration

### Chromium Bookmarks (`mindvault.bookmarks.browser.chromium`)

Export and process Chromium-based browser bookmarks.

#### ChromiumBookmarks Class

```python
class ChromiumBookmarks:
    """Export bookmarks from Chromium-based browsers."""
```

**Methods:**

```python
def export_bookmarks(browser: str = "chrome") -> list:
    """Export bookmarks from browser."""
    
def get_bookmark_file_path(browser: str = "chrome") -> str:
    """Get path to browser bookmarks file."""
    
def parse_bookmarks(file_path: str) -> list:
    """Parse bookmarks from file."""
```

**Example Usage:**

```python
from mindvault.bookmarks.browser.chromium import ChromiumBookmarks

chromium = ChromiumBookmarks()
bookmarks = chromium.export_bookmarks("chrome")
```

## Data Models

### Tweet Schema (`mindvault.bookmarks.twitter.schema`)

Data models for Twitter-related objects.

#### Tweet Model

```python
class Tweet(BaseModel):
    """Tweet data model."""
    
    tweet_id: str
    user_name: str
    user_screen_name: str
    content: str
    created_at: datetime
    retweet_count: int
    favorite_count: int
    media_urls: list[str]
    hashtags: list[str]
    mentions: list[str]
```

#### Bookmark Model

```python
class Bookmark(BaseModel):
    """Bookmark data model."""
    
    bookmark_id: str
    tweet: Tweet
    bookmarked_at: datetime
    tags: list[str]
    notes: str
```

#### ExtractedData Model

```python
class ExtractedData(BaseModel):
    """Extracted tweet data model."""
    
    tweet_id: str
    entities: dict
    topics: list[str]
    sentiment: dict
    summary: str
    key_points: list[str]
    extracted_at: datetime
```

## Error Handling

### Custom Exceptions

```python
class MindVaultError(Exception):
    """Base exception for MindVault."""
    pass

class AuthenticationError(MindVaultError):
    """Authentication failed."""
    pass

class RateLimitError(MindVaultError):
    """Rate limit exceeded."""
    pass

class DatabaseError(MindVaultError):
    """Database operation failed."""
    pass
```

### Error Handling Example

```python
from mindvault.core.exceptions import AuthenticationError, RateLimitError

try:
    exporter = BookmarksExporter()
    bookmarks = exporter.export_bookmarks()
except AuthenticationError as e:
    logger.error(f"Authentication failed: {e}")
except RateLimitError as e:
    logger.warning(f"Rate limit exceeded: {e}")
    # Implement retry logic
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Utility Functions

### Common Utilities

```python
def sanitize_filename(filename: str) -> str:
    """Sanitize filename for file system."""
    
def format_timestamp(timestamp: str) -> datetime:
    """Format timestamp string to datetime."""
    
def validate_tweet_id(tweet_id: str) -> bool:
    """Validate tweet ID format."""
    
def extract_tweet_id_from_url(url: str) -> str:
    """Extract tweet ID from Twitter URL."""
```

### Example Usage

```python
from mindvault.utils import sanitize_filename, validate_tweet_id

filename = sanitize_filename("my/file:name.txt")  # Returns "my_file_name.txt"
is_valid = validate_tweet_id("123456789")  # Returns True
```

## Configuration API

### Runtime Configuration

```python
from mindvault.core.config import settings

# Get current settings
print(f"Base directory: {settings.base_dir}")
print(f"MongoDB URI: {settings.mongodb_uri}")

# Update settings (for current session)
settings.max_concurrent_downloads = 10
settings.request_timeout = 60
```

### Environment Variables

All configuration can be set via environment variables:

```bash
export TWITTER_CT0=your_ct0_cookie
export TWITTER_AUTH_TOKEN=your_auth_token
export MONGODB_URI=mongodb://localhost:27017/
export LOG_LEVEL=DEBUG
```

## Async Operations

### Async Support

Some operations support async execution:

```python
import asyncio
from mindvault.bookmarks.twitter.async_operations import AsyncTweetProcessor

async def process_tweets_async():
    processor = AsyncTweetProcessor()
    results = await processor.process_multiple_tweets(tweet_ids)
    return results

# Run async operation
results = asyncio.run(process_tweets_async())
```

## Testing API

### Test Utilities

```python
from mindvault.testing import MockTweetData, TestDatabase

# Create mock data for testing
mock_tweet = MockTweetData.create_tweet()
mock_bookmark = MockTweetData.create_bookmark()

# Use test database
with TestDatabase() as test_db:
    # Run tests with isolated database
    test_db.insert_document("test_collection", mock_tweet)
```

## Performance Monitoring

### Performance Metrics

```python
from mindvault.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()

# Track operation performance
with monitor.track_operation("bookmark_export"):
    bookmarks = exporter.export_bookmarks()

# Get performance stats
stats = monitor.get_stats()
print(f"Average export time: {stats['bookmark_export']['avg_time']}")
```

## Plugin System

### Custom Plugins

```python
from mindvault.plugins import BasePlugin

class CustomPlugin(BasePlugin):
    """Custom plugin for MindVault."""
    
    def process_tweet(self, tweet_data: dict) -> dict:
        """Process tweet with custom logic."""
        # Your custom processing logic
        return processed_data
    
    def extract_custom_data(self, tweet_data: dict) -> dict:
        """Extract custom data from tweet."""
        # Your custom extraction logic
        return extracted_data

# Register plugin
plugin = CustomPlugin()
plugin.register()
```

## Rate Limiting

### Rate Limit Management

```python
from mindvault.rate_limiting import RateLimiter

limiter = RateLimiter(requests_per_hour=300)

# Use rate limiter
with limiter:
    response = make_api_request()
```

## Best Practices

### API Usage Guidelines

1. **Always handle exceptions** appropriately
2. **Use async operations** for better performance
3. **Implement proper logging** for debugging
4. **Validate inputs** before processing
5. **Use batch operations** for large datasets
6. **Monitor rate limits** to avoid blocking
7. **Cache results** when possible

### Example Best Practice Implementation

```python
from mindvault.core.logger_setup import get_logger
from mindvault.core.exceptions import MindVaultError

logger = get_logger(__name__)

async def process_bookmarks_safely(tweet_ids: list[str]) -> dict:
    """Process bookmarks with proper error handling."""
    results = {"success": [], "failed": []}
    
    for tweet_id in tweet_ids:
        try:
            # Validate input
            if not validate_tweet_id(tweet_id):
                raise ValueError(f"Invalid tweet ID: {tweet_id}")
            
            # Process with rate limiting
            with RateLimiter():
                result = await process_tweet_async(tweet_id)
                results["success"].append(result)
                
        except MindVaultError as e:
            logger.error(f"Failed to process tweet {tweet_id}: {e}")
            results["failed"].append({"tweet_id": tweet_id, "error": str(e)})
        except Exception as e:
            logger.error(f"Unexpected error processing tweet {tweet_id}: {e}")
            results["failed"].append({"tweet_id": tweet_id, "error": str(e)})
    
    return results
```

---

**Next Steps:**
- See [Architecture Overview](architecture.md) for system design details
- Check [User Guide](user-guide.md) for usage examples
- Review [Configuration Guide](configuration.md) for setup options