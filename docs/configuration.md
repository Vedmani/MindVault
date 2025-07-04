# Configuration Guide

This guide covers all configuration options for MindVault, from basic setup to advanced customization.

## Configuration Files

### Environment Variables (.env)

MindVault uses a `.env` file for configuration. Create one in your project root:

```env
# Twitter/X Authentication (Required)
TWITTER_CT0=your_ct0_cookie_here
TWITTER_AUTH_TOKEN=your_auth_token_here

# Optional: Separate scraper credentials for rate limiting
TWITTER_SCRAPER_CT0=your_scraper_ct0_cookie_here
TWITTER_SCRAPER_AUTH_TOKEN=your_scraper_auth_token_here

# Database Configuration
MONGODB_URI=mongodb://localhost:27017/
DB_NAME=mindvault

# Data Storage Paths (Optional - uses defaults if not specified)
BASE_DIR=/home/user/.mindvault
BOOKMARKS_PATH=${BASE_DIR}/twitter/bookmarks
TWEET_DATA_DIR=${BASE_DIR}/twitter/tweet_data
MEDIA_DIR=${BASE_DIR}/twitter/media

# Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=${BASE_DIR}/logs

# Performance Settings
MAX_CONCURRENT_DOWNLOADS=5
REQUEST_TIMEOUT=30
RETRY_ATTEMPTS=3
```

### Configuration Schema

MindVault uses Pydantic for configuration validation. Here's the complete schema:

#### Core Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `twitter_ct0` | string | Required | Twitter ct0 cookie for authentication |
| `twitter_auth_token` | string | Required | Twitter auth token for authentication |
| `twitter_scraper_ct0` | string | "" | Optional separate ct0 for scraping |
| `twitter_scraper_auth_token` | string | "" | Optional separate auth token |

#### Directory Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `base_dir` | Path | `~/.mindvault` | Base directory for all data |
| `bookmarks_path` | Path | `{base_dir}/twitter/bookmarks` | Bookmarks storage |
| `tweet_data_dir` | Path | `{base_dir}/twitter/tweet_data` | Raw tweet data |
| `extracted_data_dir` | Path | `{base_dir}/twitter/extracted_data` | Processed data |
| `media_dir` | Path | `{base_dir}/twitter/media` | Downloaded media |

#### Database Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `mongodb_uri` | string | `mongodb://localhost:27017/` | MongoDB connection string |
| `db_name` | string | `mindvault` | Database name |
| `database_url` | string | `sqlite:///{base_dir}/tweets.db` | SQLite database path |

#### Collection Names

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `raw_data_collection` | string | `raw-data` | MongoDB collection for raw data |
| `extracted_data_collection` | string | `extracted-data` | Processed data collection |
| `bookmarks_collection` | string | `bookmarks` | Bookmarks collection |
| `scraper_collection` | string | `scraper` | Scraper data collection |

## Authentication Setup

### Twitter/X Cookies

#### Method 1: Browser Developer Tools

1. **Open Twitter/X** in your browser and log in
2. **Open Developer Tools** (F12)
3. **Navigate to Application/Storage tab**
4. **Find Cookies** for twitter.com
5. **Copy these values**:
   - `ct0` cookie value
   - `auth_token` cookie value

#### Method 2: Using Browser Extensions

Install a cookie manager extension like "Cookie Editor" to easily extract cookies.

#### Method 3: Using Scripts

```python
# Example script to extract cookies (requires selenium)
from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.get("https://twitter.com")
# Manual login required
input("Press Enter after logging in...")

cookies = driver.get_cookies()
for cookie in cookies:
    if cookie['name'] in ['ct0', 'auth_token']:
        print(f"{cookie['name']}: {cookie['value']}")
```

### Rate Limiting with Separate Credentials

For heavy usage, configure separate scraper credentials:

```env
# Main account credentials (for bookmarks)
TWITTER_CT0=main_account_ct0
TWITTER_AUTH_TOKEN=main_account_auth_token

# Scraper account credentials (for data collection)
TWITTER_SCRAPER_CT0=scraper_account_ct0
TWITTER_SCRAPER_AUTH_TOKEN=scraper_account_auth_token
```

## Database Configuration

### MongoDB Setup

#### Local MongoDB

```env
MONGODB_URI=mongodb://localhost:27017/
DB_NAME=mindvault
```

#### MongoDB Atlas (Cloud)

```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
DB_NAME=mindvault
```

#### MongoDB with Authentication

```env
MONGODB_URI=mongodb://username:password@localhost:27017/
DB_NAME=mindvault
```

### SQLite Configuration

SQLite is used for lightweight data storage:

```env
DATABASE_URL=sqlite:////path/to/your/tweets.db
```

## Directory Structure Customization

### Default Structure

```
~/.mindvault/
├── twitter/
│   ├── bookmarks/           # Exported bookmarks
│   ├── tweet_ids/          # Tweet ID lists
│   ├── tweet_data/         # Raw tweet JSON data
│   ├── extracted_data/     # AI-processed data
│   ├── media/              # Downloaded images/videos
│   ├── tweets.db           # SQLite database
│   └── pending_tweets.json # Processing queue
└── logs/                   # Application logs
```

### Custom Paths

```env
BASE_DIR=/custom/path/mindvault
BOOKMARKS_PATH=/custom/bookmarks/path
TWEET_DATA_DIR=/custom/tweets/path
MEDIA_DIR=/custom/media/path
```

## Performance Tuning

### Concurrent Downloads

```env
MAX_CONCURRENT_DOWNLOADS=10  # Increase for faster downloads
REQUEST_TIMEOUT=60          # Increase for slow connections
RETRY_ATTEMPTS=5           # Increase for unreliable connections
```

### Memory Usage

```env
BATCH_SIZE=100             # Reduce for lower memory usage
CACHE_SIZE=1000           # Adjust based on available RAM
```

## Logging Configuration

### Log Levels

```env
LOG_LEVEL=DEBUG    # Most verbose
LOG_LEVEL=INFO     # General information
LOG_LEVEL=WARNING  # Warnings only
LOG_LEVEL=ERROR    # Errors only
```

### Custom Log Directory

```env
LOG_DIR=/custom/log/path
LOG_ROTATION=daily         # daily, weekly, monthly
LOG_MAX_SIZE=10MB         # Maximum log file size
```

## Advanced Configuration

### Custom Settings Class

For programmatic configuration:

```python
from mindvault.core.config import Settings

# Custom settings
class CustomSettings(Settings):
    custom_api_key: str = "your-api-key"
    custom_endpoint: str = "https://api.example.com"
    
    class Config:
        env_prefix = "MINDVAULT_"

settings = CustomSettings()
```

### Runtime Configuration

```python
from mindvault.core.config import settings

# Override settings at runtime
settings.max_concurrent_downloads = 20
settings.request_timeout = 120
```

## Environment-Specific Configurations

### Development Environment

```env
LOG_LEVEL=DEBUG
MAX_CONCURRENT_DOWNLOADS=2
REQUEST_TIMEOUT=10
DB_NAME=mindvault_dev
```

### Production Environment

```env
LOG_LEVEL=INFO
MAX_CONCURRENT_DOWNLOADS=10
REQUEST_TIMEOUT=30
DB_NAME=mindvault_prod
MONGODB_URI=mongodb+srv://prod-user:password@cluster.mongodb.net/
```

### Testing Environment

```env
LOG_LEVEL=ERROR
DB_NAME=mindvault_test
MONGODB_URI=mongodb://localhost:27017/
SKIP_DOWNLOADS=true
```

## Configuration Validation

MindVault validates configuration on startup:

```python
from mindvault.core.config import settings

# This will raise an error if configuration is invalid
try:
    settings.validate_mongodb_connection()
    print("Configuration is valid!")
except Exception as e:
    print(f"Configuration error: {e}")
```

## Common Configuration Issues

### 1. Missing Required Settings

```bash
# Error: Missing TWITTER_CT0
export TWITTER_CT0=your_ct0_value
```

### 2. Invalid MongoDB URI

```bash
# Error: Connection failed
# Check MongoDB service status
sudo systemctl status mongod
```

### 3. Path Permission Issues

```bash
# Error: Permission denied
# Fix directory permissions
chmod 755 ~/.mindvault
```

### 4. Port Conflicts

```bash
# Error: Port already in use
# Change MongoDB port
MONGODB_URI=mongodb://localhost:27018/
```

## Configuration Best Practices

1. **Use Environment Variables**: Never hardcode credentials
2. **Separate Environments**: Use different configs for dev/prod
3. **Regular Backups**: Backup your configuration files
4. **Monitor Logs**: Check logs for configuration issues
5. **Version Control**: Track configuration changes (without secrets)

## Security Considerations

1. **Protect Credentials**: Never commit `.env` files
2. **Use Strong Passwords**: For database authentication
3. **Rotate Tokens**: Regularly update Twitter tokens
4. **Limit Permissions**: Use least-privilege access
5. **Monitor Usage**: Track API usage and limits

## Troubleshooting

### Configuration Validation

```python
from mindvault.core.config import settings

# Check current configuration
print(f"Base directory: {settings.base_dir}")
print(f"MongoDB URI: {settings.mongodb_uri}")
print(f"Database name: {settings.db_name}")
```

### Common Issues

1. **Environment Variables Not Loading**
   - Check `.env` file location
   - Verify environment variable names
   - Restart application after changes

2. **Database Connection Fails**
   - Verify MongoDB is running
   - Check network connectivity
   - Validate credentials

3. **Permission Errors**
   - Check directory permissions
   - Verify write access to data directories
   - Run with appropriate user permissions

---

**Next Steps**: After configuration, see the [User Guide](user-guide.md) to start using MindVault.