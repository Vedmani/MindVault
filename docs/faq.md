# Frequently Asked Questions (FAQ)

This document answers common questions about MindVault installation, usage, and troubleshooting.

## General Questions

### What is MindVault?

MindVault is an AI-powered personal knowledge assistant that transforms your digital footprint into an intelligent knowledge base. It primarily focuses on processing Twitter/X bookmarks and browser data to extract meaningful insights using artificial intelligence.

### What makes MindVault different from other bookmark managers?

MindVault goes beyond simple bookmark storage by:
- **AI-powered content analysis**: Extracting entities, topics, and sentiment from your bookmarks
- **Media management**: Automatically downloading and organizing media content
- **Intelligent search**: Finding content based on semantic meaning, not just keywords
- **Cross-platform support**: Working with Twitter/X, browser bookmarks, and more
- **Extensible architecture**: Supporting custom plugins and workflows

### Is MindVault free?

MindVault is an open-source project. The core software is free to use, but you may need to provide your own:
- AI service API keys (Google GenAI, OpenAI, etc.)
- Database hosting (MongoDB)
- Twitter/X account for authentication

## Installation and Setup

### What are the system requirements?

- **Python**: 3.12 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: At least 1GB free space
- **Database**: MongoDB (local or cloud)
- **Browser**: Chromium-based browser for automation

### How do I get Twitter/X authentication tokens?

1. **Browser Method** (Recommended):
   - Open Twitter/X in your browser and log in
   - Open Developer Tools (F12)
   - Go to Application/Storage tab
   - Find cookies for twitter.com
   - Copy `ct0` and `auth_token` values

2. **Browser Extension Method**:
   - Install a cookie manager extension like "Cookie Editor"
   - Navigate to Twitter/X
   - Extract the required cookies

### Why do I need MongoDB?

MongoDB is used for:
- **Flexible data storage**: Handling varying tweet structures
- **Scalability**: Managing large amounts of bookmark data
- **Query performance**: Fast searching and filtering
- **AI integration**: Storing processed results and embeddings

You can use either local MongoDB or cloud services like MongoDB Atlas.

### Can I use MindVault without MongoDB?

Currently, MongoDB is required for full functionality. However, you can:
- Use MongoDB Atlas free tier (cloud)
- Run MongoDB locally with minimal resources
- Use Docker to simplify MongoDB setup

Future versions may support additional database options.

## Usage and Features

### How do I export my Twitter bookmarks?

```python
from mindvault.bookmarks.twitter import BookmarksExporter

exporter = BookmarksExporter()
bookmarks = exporter.export_bookmarks()
```

Or use the command line:
```bash
mindvault export-bookmarks
```

### How long does it take to process bookmarks?

Processing time depends on:
- **Number of bookmarks**: 100 bookmarks typically take 5-10 minutes
- **AI processing**: Each tweet analysis takes 1-3 seconds
- **Media downloads**: Depends on file sizes and internet speed
- **System resources**: More RAM/CPU = faster processing

### Can I process bookmarks in batches?

Yes! You can process bookmarks in smaller batches:

```python
from mindvault.bookmarks.twitter.workflow import BatchProcessor

processor = BatchProcessor()
processor.process_batch(batch_size=50)
```

### What AI models does MindVault use?

MindVault supports multiple AI providers:
- **Google GenAI**: Primary AI processing (Gemini models)
- **OpenAI**: GPT models for text analysis
- **LiteLLM**: Multi-model support for various providers
- **Local models**: Support for self-hosted AI models

### How accurate is the AI analysis?

AI accuracy depends on:
- **Model quality**: Newer models generally perform better
- **Content type**: Some topics analyzed better than others
- **Language**: English content typically has highest accuracy
- **Context**: Longer content provides better analysis

Typical accuracy ranges:
- **Entity extraction**: 85-95%
- **Topic classification**: 80-90%
- **Sentiment analysis**: 90-95%

## Troubleshooting

### "Authentication failed" error

**Possible causes:**
1. **Invalid cookies**: Twitter tokens may have expired
2. **Incorrect format**: Cookie values might be incorrectly copied
3. **Account restrictions**: Your Twitter account may be limited

**Solutions:**
1. Re-extract cookies from browser
2. Verify cookie values are complete
3. Try with a different Twitter account
4. Check if you're logged into Twitter in the browser

### "MongoDB connection failed" error

**Possible causes:**
1. **MongoDB not running**: Service not started
2. **Wrong connection string**: Incorrect URI
3. **Network issues**: Firewall or connectivity problems
4. **Authentication issues**: Wrong username/password

**Solutions:**
```bash
# Check MongoDB status
sudo systemctl status mongod

# Start MongoDB
sudo systemctl start mongod

# Test connection
mongo --host localhost:27017
```

### "Rate limit exceeded" error

**Possible causes:**
1. **Twitter rate limits**: Too many requests to Twitter API
2. **AI service limits**: Exceeded API quotas
3. **Concurrent requests**: Too many simultaneous operations

**Solutions:**
1. **Wait and retry**: Rate limits reset after time
2. **Use separate credentials**: Configure scraper tokens
3. **Reduce concurrency**: Lower `max_concurrent_downloads`
4. **Implement delays**: Add delays between requests

### "Permission denied" error

**Possible causes:**
1. **File permissions**: Cannot write to data directory
2. **Directory ownership**: Wrong user/group ownership
3. **Disk space**: Insufficient storage space

**Solutions:**
```bash
# Fix permissions
chmod 755 ~/.mindvault
chown -R $USER:$USER ~/.mindvault

# Check disk space
df -h ~/.mindvault
```

### Memory errors during processing

**Possible causes:**
1. **Large datasets**: Processing too many bookmarks at once
2. **Media files**: Large media downloads
3. **Memory leaks**: Long-running processes

**Solutions:**
1. **Process in batches**: Reduce batch size
2. **Increase swap**: Add virtual memory
3. **Restart process**: Clear memory periodically
4. **Limit concurrent downloads**: Reduce parallel operations

## Performance and Optimization

### How can I speed up processing?

1. **Increase concurrency**:
   ```python
   settings.max_concurrent_downloads = 10
   ```

2. **Use SSD storage**: Faster disk I/O
3. **More RAM**: Enables larger batch processing
4. **Better internet**: Faster API calls and downloads
5. **Local AI models**: Reduce API latency

### Why is media download slow?

**Common causes:**
1. **Large files**: High-resolution images and videos
2. **Network speed**: Slow internet connection
3. **Rate limiting**: Twitter throttling downloads
4. **Concurrent limit**: Too many simultaneous downloads

**Solutions:**
1. **Skip large files**: Set file size limits
2. **Download later**: Queue for off-peak hours
3. **Increase timeout**: Allow more time for downloads
4. **Use faster network**: Switch to better connection

### Can I run MindVault on a server?

Yes! MindVault works well on servers:

**Benefits:**
- **24/7 operation**: Continuous processing
- **Better resources**: More RAM and CPU
- **Scheduled processing**: Automated workflows
- **Remote access**: Access from anywhere

**Considerations:**
- **Headless operation**: No GUI browser for cookie extraction
- **Security**: Secure credential storage
- **Monitoring**: Log monitoring and alerting
- **Backup**: Regular data backups

## Data Management

### Where is my data stored?

Default locations:
- **Configuration**: `~/.mindvault/config/`
- **Tweet data**: `~/.mindvault/twitter/tweet_data/`
- **Media files**: `~/.mindvault/twitter/media/`
- **Database**: MongoDB collections
- **Logs**: `~/.mindvault/logs/`

### How do I backup my data?

1. **Database backup**:
   ```bash
   mongodump --db mindvault --out backup/
   ```

2. **File system backup**:
   ```bash
   tar -czf mindvault-backup.tar.gz ~/.mindvault/
   ```

3. **Export data**:
   ```python
   # Export to JSON
   db.export_collection("bookmarks", "bookmarks.json")
   ```

### Can I delete old data?

Yes, you can clean up old data:

```python
from mindvault.core.mongodb_utils import MongoDBUtils

db = MongoDBUtils()

# Delete data older than 6 months
import datetime
cutoff_date = datetime.datetime.now() - datetime.timedelta(days=180)
db.delete_documents("bookmarks", {"created_at": {"$lt": cutoff_date}})
```

### How do I migrate to a new machine?

1. **Export data**:
   ```bash
   # Database
   mongodump --db mindvault --out backup/
   
   # Files
   tar -czf mindvault-files.tar.gz ~/.mindvault/
   ```

2. **Transfer files** to new machine

3. **Import data**:
   ```bash
   # Database
   mongorestore --db mindvault backup/mindvault/
   
   # Files
   tar -xzf mindvault-files.tar.gz
   ```

## Integration and Customization

### Can I add custom AI models?

Yes! MindVault supports custom AI integrations:

```python
from mindvault.bookmarks.twitter.extract import BaseExtractor

class CustomExtractor(BaseExtractor):
    def extract_entities(self, text):
        # Your custom AI logic here
        return custom_analysis
```

### How do I create custom workflows?

```python
from mindvault.bookmarks.twitter.workflow import BaseWorkflow

class CustomWorkflow(BaseWorkflow):
    def process(self, data):
        # Your custom processing logic
        return processed_data

# Register workflow
workflow = CustomWorkflow()
workflow.register()
```

### Can I integrate with other services?

Yes! MindVault is designed to be extensible:

**Supported integrations:**
- **Browser bookmarks**: Chrome, Firefox, Safari
- **Note-taking apps**: Notion, Obsidian (via plugins)
- **Cloud storage**: Google Drive, Dropbox
- **Analytics**: Custom dashboards and reports

**Plugin development:**
```python
from mindvault.plugins import BasePlugin

class CustomPlugin(BasePlugin):
    def process_data(self, data):
        # Your integration logic
        return processed_data
```

## Privacy and Security

### Is my data secure?

MindVault takes security seriously:

**Data protection:**
- **Local storage**: Data stays on your machine by default
- **Encryption**: Sensitive data is encrypted
- **Access control**: Only you have access to your data
- **No tracking**: No usage analytics or tracking

**Authentication:**
- **Secure storage**: Credentials stored safely
- **Token rotation**: Support for refreshing tokens
- **Access logging**: Monitor authentication attempts

### What data does MindVault collect?

MindVault only processes data you explicitly provide:
- **Twitter bookmarks**: Only bookmarks you choose to export
- **Browser data**: Only bookmarks you select
- **AI processing**: Only content you send for analysis

**No data is sent to MindVault developers or third parties.**

### Can I use MindVault offline?

Partially:
- **Local data**: Access stored data offline
- **File operations**: Organize and search local files
- **Database queries**: Query local MongoDB

**Requires internet:**
- **Twitter API**: Fetching new bookmarks
- **AI processing**: Most AI models require API access
- **Media downloads**: Downloading new media content

### How do I delete my data?

Complete data removal:

```bash
# Stop MindVault services
mindvault stop

# Remove all data
rm -rf ~/.mindvault/

# Drop MongoDB collections
mongo mindvault --eval "db.dropDatabase()"
```

## Support and Community

### Where can I get help?

1. **Documentation**: Check our comprehensive docs
2. **GitHub Issues**: Report bugs and request features
3. **Discussions**: Join community discussions
4. **Email**: Contact developers directly

### How do I report a bug?

1. **Check existing issues**: Search GitHub issues first
2. **Gather information**:
   - Error messages
   - System information
   - Steps to reproduce
   - Configuration details

3. **Create issue**: Use our bug report template
4. **Provide logs**: Include relevant log files

### Can I contribute to MindVault?

Yes! We welcome contributions:

- **Code**: Bug fixes, new features, optimizations
- **Documentation**: Improve docs, add examples
- **Testing**: Report bugs, test new features
- **Feedback**: Share ideas and suggestions

See our [Contributing Guide](../contributing.md) for details.

### What's the roadmap for MindVault?

**Upcoming features:**
- **Web interface**: Browser-based UI
- **Mobile app**: iOS and Android support
- **More integrations**: Additional social media platforms
- **Advanced AI**: Better analysis and insights
- **Collaboration**: Sharing and team features

**Long-term goals:**
- **Enterprise features**: Team management and analytics
- **Cloud hosting**: Managed MindVault service
- **Marketplace**: Plugin and integration marketplace

---

**Still have questions?** 

- 📖 Check our [documentation](installation.md)
- 💬 Join our [community discussions](https://github.com/yourusername/mindvault/discussions)
- 🐛 Report [issues](https://github.com/yourusername/mindvault/issues)
- 📧 Contact us directly