# User Guide

This comprehensive guide will walk you through using MindVault to transform your digital footprint into an intelligent knowledge base.

## Getting Started

### First Run

After installation and configuration, initialize MindVault:

```bash
# Initialize MindVault
mindvault

# Check status
mindvault --status
```

### Basic Workflow

1. **Export bookmarks** from Twitter/X
2. **Process tweets** with AI analysis
3. **Download media** content
4. **Query knowledge base** for insights

## Core Features

### Twitter/X Integration

#### Exporting Bookmarks

```python
from mindvault.bookmarks.twitter import export_bookmarks

# Export your Twitter bookmarks
export_bookmarks()
```

Command line usage:
```bash
mindvault export-bookmarks
```

#### Processing Tweet Data

```python
from mindvault.bookmarks.twitter import process_tweets

# Process exported tweets
process_tweets()
```

### Browser Automation

#### Chromium Integration

```python
from mindvault.bookmarks.browser import ChromiumBookmarks

# Export browser bookmarks
chromium = ChromiumBookmarks()
bookmarks = chromium.export_bookmarks()
```

### Data Processing

#### AI-Powered Content Extraction

```python
from mindvault.bookmarks.twitter.extract import TweetExtractor

# Extract insights from tweets
extractor = TweetExtractor()
insights = extractor.extract_tweet_data(tweet_id)
```

## Working with Bookmarks

### Export Process

1. **Authentication Check**
   ```python
   from mindvault.core.config import settings
   
   # Verify Twitter credentials
   auth = settings.get_bookmarks_auth()
   print(f"Using credentials: {auth}")
   ```

2. **Export Bookmarks**
   ```python
   from mindvault.bookmarks.twitter.bookmarks import BookmarksExporter
   
   exporter = BookmarksExporter()
   bookmarks = exporter.export_all()
   ```

3. **Process Tweet Data**
   ```python
   from mindvault.bookmarks.twitter.workflow import process_bookmarks
   
   # Full processing pipeline
   process_bookmarks()
   ```

### Bookmark Management

#### View Bookmarks

```python
from mindvault.bookmarks.twitter.database import BookmarkDB

db = BookmarkDB()
bookmarks = db.get_all_bookmarks()

for bookmark in bookmarks:
    print(f"Tweet: {bookmark.tweet_id}")
    print(f"User: {bookmark.user_name}")
    print(f"Date: {bookmark.created_at}")
```

#### Search Bookmarks

```python
# Search by keyword
results = db.search_bookmarks("AI", "machine learning")

# Search by user
user_bookmarks = db.get_bookmarks_by_user("username")

# Search by date range
recent_bookmarks = db.get_bookmarks_by_date_range(
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

## Media Management

### Downloading Media

```python
from mindvault.bookmarks.twitter.download_tweet_media import TweetMediaDownloader

downloader = TweetMediaDownloader()

# Download media for a specific tweet
downloader.download_tweet_media(tweet_id)

# Download all pending media
downloader.download_pending_media()
```

### Media Organization

Media files are organized by date and type:

```
~/.mindvault/twitter/media/
├── 2024/
│   ├── 01/
│   │   ├── images/
│   │   │   ├── tweet_123_image_1.jpg
│   │   │   └── tweet_123_image_2.png
│   │   └── videos/
│   │       └── tweet_456_video_1.mp4
│   └── 02/
│       └── ...
```

## Data Analysis

### AI-Powered Insights

```python
from mindvault.bookmarks.twitter.extract import TweetExtractor

extractor = TweetExtractor()

# Extract entities and topics
analysis = extractor.extract_entities(tweet_text)
print(f"Entities: {analysis.entities}")
print(f"Topics: {analysis.topics}")
print(f"Sentiment: {analysis.sentiment}")
```

### Querying Your Knowledge Base

```python
from mindvault.core.mongodb_utils import MongoDBUtils

db = MongoDBUtils()

# Find tweets about specific topics
ai_tweets = db.query_collection(
    "extracted-data",
    {"topics": {"$in": ["AI", "machine learning"]}}
)

# Find tweets by sentiment
positive_tweets = db.query_collection(
    "extracted-data",
    {"sentiment": "positive"}
)
```

## Advanced Usage

### Batch Processing

```python
from mindvault.bookmarks.twitter.workflow import BatchProcessor

processor = BatchProcessor()

# Process tweets in batches
processor.process_batch(
    batch_size=100,
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

### Custom Extractors

```python
from mindvault.bookmarks.twitter.extract import BaseExtractor

class CustomExtractor(BaseExtractor):
    def extract_custom_data(self, tweet_data):
        # Your custom extraction logic
        return {
            "custom_field": "custom_value",
            "processed_at": datetime.now()
        }

# Use custom extractor
extractor = CustomExtractor()
custom_data = extractor.extract_custom_data(tweet_data)
```

### Workflow Automation

```python
from mindvault.bookmarks.twitter.workflow import AutomatedWorkflow

workflow = AutomatedWorkflow()

# Set up automated processing
workflow.setup_scheduler(
    interval="daily",
    time="02:00",
    tasks=["export_bookmarks", "process_tweets", "download_media"]
)
```

## Database Operations

### MongoDB Operations

```python
from mindvault.core.mongodb_utils import MongoDBUtils

db = MongoDBUtils()

# Insert data
db.insert_document("my-collection", {"key": "value"})

# Query data
results = db.query_collection("my-collection", {"key": "value"})

# Update data
db.update_document("my-collection", {"key": "value"}, {"$set": {"new_key": "new_value"}})

# Delete data
db.delete_document("my-collection", {"key": "value"})
```

### SQLite Operations

```python
from mindvault.bookmarks.twitter.database import BookmarkDB

db = BookmarkDB()

# Execute custom query
results = db.execute_query(
    "SELECT * FROM bookmarks WHERE user_name = ?",
    ("username",)
)
```

## Performance Optimization

### Concurrent Processing

```python
from mindvault.core.config import settings

# Adjust concurrent downloads
settings.max_concurrent_downloads = 10

# Adjust request timeout
settings.request_timeout = 60
```

### Memory Management

```python
# Process in smaller batches to manage memory
processor.process_batch(batch_size=50)

# Clear cache periodically
processor.clear_cache()
```

## Monitoring and Logging

### Viewing Logs

```bash
# View recent logs
tail -f ~/.mindvault/logs/mindvault.log

# View error logs only
grep "ERROR" ~/.mindvault/logs/mindvault.log
```

### Custom Logging

```python
from mindvault.core.logger_setup import get_logger

logger = get_logger(__name__)

logger.info("Processing started")
logger.warning("Rate limit approaching")
logger.error("Processing failed")
```

## Common Workflows

### Daily Bookmark Processing

```python
def daily_workflow():
    """Daily automated workflow"""
    from mindvault.bookmarks.twitter.workflow import process_bookmarks
    
    # Export new bookmarks
    process_bookmarks()
    
    # Download new media
    download_pending_media()
    
    # Generate daily report
    generate_daily_report()

# Schedule daily workflow
schedule_workflow(daily_workflow, interval="daily")
```

### Research Project Setup

```python
def setup_research_project(topic):
    """Set up a research project for a specific topic"""
    
    # Create project directory
    project_dir = Path(f"~/.mindvault/research/{topic}")
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Export bookmarks related to topic
    topic_bookmarks = db.search_bookmarks(topic)
    
    # Process with specialized extractors
    for bookmark in topic_bookmarks:
        process_research_tweet(bookmark, topic)
```

## Troubleshooting

### Common Issues

#### 1. Rate Limiting

```python
# Check rate limit status
from mindvault.bookmarks.twitter.api import check_rate_limit

status = check_rate_limit()
print(f"Remaining requests: {status['remaining']}")
print(f"Reset time: {status['reset_time']}")
```

#### 2. Authentication Errors

```python
# Verify credentials
from mindvault.core.config import settings

try:
    auth = settings.get_bookmarks_auth()
    # Test authentication
    test_auth(auth)
except Exception as e:
    print(f"Authentication failed: {e}")
```

#### 3. Database Connection Issues

```python
# Test database connection
from mindvault.core.mongodb_utils import MongoDBUtils

try:
    db = MongoDBUtils()
    db.test_connection()
    print("Database connection successful")
except Exception as e:
    print(f"Database connection failed: {e}")
```

### Getting Help

1. **Check logs**: `~/.mindvault/logs/`
2. **Verify configuration**: See [Configuration Guide](configuration.md)
3. **Read FAQ**: [FAQ](faq.md)
4. **GitHub Issues**: Report bugs or request features

## Best Practices

1. **Regular Backups**: Export your data regularly
2. **Monitor Usage**: Keep track of API limits
3. **Update Credentials**: Refresh Twitter tokens periodically
4. **Clean Up**: Remove old data files when needed
5. **Version Control**: Track your custom extractors and workflows

## Tips and Tricks

### Keyboard Shortcuts

```bash
# Quick status check
alias mvs='mindvault --status'

# Quick export
alias mve='mindvault export-bookmarks'

# Quick processing
alias mvp='mindvault process-tweets'
```

### Custom Commands

```python
# Add to your .bashrc or .zshrc
def mv_daily() {
    mindvault export-bookmarks
    mindvault process-tweets
    mindvault download-media
    echo "Daily MindVault processing completed!"
}
```

### Data Analysis Scripts

```python
# Create analysis scripts
def analyze_bookmark_trends():
    """Analyze bookmark trends over time"""
    bookmarks = db.get_all_bookmarks()
    
    # Group by month
    monthly_counts = {}
    for bookmark in bookmarks:
        month = bookmark.created_at.strftime("%Y-%m")
        monthly_counts[month] = monthly_counts.get(month, 0) + 1
    
    return monthly_counts
```

---

**Next Steps**: 
- Explore [API Documentation](api.md) for advanced usage
- Check [Architecture Overview](architecture.md) to understand the system
- Join the community for tips and support