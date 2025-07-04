# Architecture Overview

This document provides a comprehensive overview of MindVault's architecture, design principles, and system components.

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        MindVault System                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   User Interface │  │   API Layer     │  │   CLI Tools     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Core Engine   │  │   Workflow Mgr  │  │   Config Mgr    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Twitter API   │  │   Browser API   │  │   AI Services   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   MongoDB       │  │   SQLite        │  │   File System   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Layers

1. **Presentation Layer**: User interfaces, CLI tools, and API endpoints
2. **Application Layer**: Core business logic and workflow management
3. **Service Layer**: External service integrations and AI processing
4. **Data Layer**: Data storage and persistence management

## Core Components

### 1. Configuration Management (`mindvault.core.config`)

**Purpose**: Centralized configuration management using Pydantic settings.

**Key Features**:
- Environment variable loading
- Configuration validation
- Type safety
- Default value management

**Design Pattern**: Singleton pattern for global configuration access.

```python
class Settings(BaseSettings):
    # Configuration schema with validation
    twitter_ct0: str
    twitter_auth_token: str
    mongodb_uri: str = "mongodb://localhost:27017/"
    base_dir: Path = Path.home() / ".mindvault"
```

### 2. Data Storage Layer

#### MongoDB Integration
- **Purpose**: Document-based storage for flexible data structures
- **Collections**:
  - `raw-data`: Original tweet data
  - `extracted-data`: AI-processed content
  - `bookmarks`: User bookmarks
  - `scraper`: Web scraping results

#### SQLite Integration
- **Purpose**: Lightweight relational data for structured queries
- **Tables**:
  - `tweets`: Tweet metadata
  - `users`: User information
  - `media`: Media file references

### 3. Twitter/X Integration Layer

#### Bookmark Export System
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Authentication│───▶│   API Client    │───▶│   Data Parser   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   File Storage  │◀───│   Data Validator│◀───│   JSON Handler  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### Tweet Processing Pipeline
```
Tweet Data Input
      │
      ▼
┌─────────────────┐
│   Data Cleaning │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│   AI Processing │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│   Data Storage  │
└─────────────────┘
```

### 4. AI Processing Engine

#### Content Extraction Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Text Input    │───▶│   Preprocessor  │───▶│   AI Models     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Structured    │◀───│   Postprocessor │◀───│   Raw Results   │
│   Output        │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**AI Services Integration**:
- **Google GenAI**: Primary AI processing
- **LiteLLM**: Multi-model support
- **Instructor**: Structured output generation

### 5. Browser Automation Layer

#### Chromium Integration
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Playwright    │───▶│   Browser       │───▶│   Page Actions  │
│   Controller    │    │   Instance      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Export   │◀───│   DOM Parser    │◀───│   Content       │
│                 │    │                 │    │   Extractor     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 6. Workflow Management System

#### Workflow Orchestration
```
┌─────────────────┐
│   Workflow      │
│   Definition    │
└─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Task Queue    │───▶│   Executor      │───▶│   Result        │
│                 │    │                 │    │   Handler       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Workflow Types**:
- **Sequential**: Tasks execute in order
- **Parallel**: Tasks execute concurrently
- **Conditional**: Tasks execute based on conditions
- **Scheduled**: Tasks execute on schedule

## Data Flow Architecture

### 1. Bookmark Export Flow

```
User Request
    │
    ▼
┌─────────────────┐
│   Authenticate  │
│   with Twitter  │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   Fetch         │
│   Bookmarks     │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   Parse &       │
│   Validate      │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   Store in      │
│   Database      │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   Queue for     │
│   Processing    │
└─────────────────┘
```

### 2. Content Processing Flow

```
Tweet Data
    │
    ▼
┌─────────────────┐
│   Text          │
│   Extraction    │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   AI Analysis   │
│   (Entities,    │
│   Sentiment,    │
│   Topics)       │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   Media         │
│   Download      │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   Store         │
│   Processed     │
│   Data          │
└─────────────────┘
```

### 3. Media Management Flow

```
Media URLs
    │
    ▼
┌─────────────────┐
│   URL           │
│   Validation    │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   Download      │
│   Queue         │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   Concurrent    │
│   Downloads     │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   File          │
│   Organization  │
└─────────────────┘
```

## Design Patterns

### 1. Repository Pattern
Used for data access abstraction:

```python
class BookmarkRepository:
    def __init__(self, db_client):
        self.db = db_client
    
    def save(self, bookmark):
        return self.db.insert_document("bookmarks", bookmark)
    
    def find_by_id(self, bookmark_id):
        return self.db.query_collection("bookmarks", {"_id": bookmark_id})
```

### 2. Factory Pattern
Used for creating service instances:

```python
class ServiceFactory:
    @staticmethod
    def create_extractor(provider: str):
        if provider == "openai":
            return OpenAIExtractor()
        elif provider == "google":
            return GoogleExtractor()
        else:
            raise ValueError(f"Unknown provider: {provider}")
```

### 3. Observer Pattern
Used for workflow event handling:

```python
class WorkflowObserver:
    def on_task_start(self, task_name):
        logger.info(f"Task {task_name} started")
    
    def on_task_complete(self, task_name, result):
        logger.info(f"Task {task_name} completed: {result}")
```

### 4. Strategy Pattern
Used for different processing strategies:

```python
class ProcessingStrategy:
    def process(self, data):
        raise NotImplementedError

class TwitterStrategy(ProcessingStrategy):
    def process(self, data):
        # Twitter-specific processing
        pass

class BrowserStrategy(ProcessingStrategy):
    def process(self, data):
        # Browser bookmark processing
        pass
```

## Database Schema Design

### MongoDB Collections

#### 1. Raw Data Collection
```json
{
  "_id": "ObjectId",
  "tweet_id": "string",
  "user_id": "string",
  "content": "string",
  "created_at": "datetime",
  "media_urls": ["string"],
  "hashtags": ["string"],
  "mentions": ["string"],
  "raw_data": "object",
  "imported_at": "datetime"
}
```

#### 2. Extracted Data Collection
```json
{
  "_id": "ObjectId",
  "tweet_id": "string",
  "entities": {
    "people": ["string"],
    "organizations": ["string"],
    "locations": ["string"],
    "technologies": ["string"]
  },
  "topics": ["string"],
  "sentiment": {
    "score": "float",
    "label": "string"
  },
  "summary": "string",
  "key_points": ["string"],
  "extracted_at": "datetime"
}
```

### SQLite Schema

#### 1. Bookmarks Table
```sql
CREATE TABLE bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT UNIQUE NOT NULL,
    user_name TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    bookmarked_at DATETIME NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    INDEX idx_tweet_id (tweet_id),
    INDEX idx_user_name (user_name),
    INDEX idx_created_at (created_at)
);
```

#### 2. Media Table
```sql
CREATE TABLE media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT NOT NULL,
    media_url TEXT NOT NULL,
    local_path TEXT,
    media_type TEXT NOT NULL,
    downloaded_at DATETIME,
    file_size INTEGER,
    FOREIGN KEY (tweet_id) REFERENCES bookmarks(tweet_id)
);
```

## Security Architecture

### 1. Authentication Management
- Secure credential storage
- Token rotation support
- Authentication validation
- Error handling for auth failures

### 2. Data Protection
- Sensitive data encryption
- Secure file permissions
- Database connection security
- API key management

### 3. Rate Limiting
- Request throttling
- Backoff strategies
- Quota management
- Usage monitoring

## Performance Optimizations

### 1. Concurrent Processing
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_tweets_concurrently(tweet_ids):
    with ThreadPoolExecutor(max_workers=10) as executor:
        tasks = [
            loop.run_in_executor(executor, process_tweet, tweet_id)
            for tweet_id in tweet_ids
        ]
        return await asyncio.gather(*tasks)
```

### 2. Caching Strategy
- In-memory caching for frequently accessed data
- File-based caching for processed results
- Cache invalidation strategies
- Cache size management

### 3. Batch Processing
- Bulk database operations
- Batch API requests
- Parallel processing of batches
- Memory-efficient processing

## Error Handling and Resilience

### 1. Error Hierarchy
```python
class MindVaultError(Exception):
    """Base exception for all MindVault errors"""
    pass

class AuthenticationError(MindVaultError):
    """Authentication-related errors"""
    pass

class RateLimitError(MindVaultError):
    """Rate limiting errors"""
    pass

class DataProcessingError(MindVaultError):
    """Data processing errors"""
    pass
```

### 2. Retry Mechanisms
- Exponential backoff for API calls
- Configurable retry counts
- Circuit breaker pattern
- Graceful degradation

### 3. Monitoring and Logging
- Structured logging with context
- Performance metrics collection
- Error tracking and alerting
- Health check endpoints

## Extensibility and Plugins

### 1. Plugin Architecture
```python
class BasePlugin:
    def __init__(self):
        self.name = self.__class__.__name__
    
    def register(self):
        """Register the plugin with the system"""
        pass
    
    def process(self, data):
        """Process data with plugin logic"""
        raise NotImplementedError
```

### 2. Hook System
- Pre/post processing hooks
- Event-driven architecture
- Plugin dependency management
- Configuration validation

## Future Architecture Considerations

### 1. Microservices Migration
- Service decomposition strategy
- API gateway implementation
- Service discovery mechanism
- Inter-service communication

### 2. Scalability Improvements
- Horizontal scaling support
- Load balancing strategies
- Database sharding
- Caching layer enhancements

### 3. Cloud-Native Features
- Container orchestration
- Auto-scaling capabilities
- Managed service integration
- Serverless computing support

## Development Guidelines

### 1. Code Organization
- Clear module separation
- Dependency injection
- Interface-based design
- Test-driven development

### 2. Documentation Standards
- Comprehensive docstrings
- API documentation
- Architecture diagrams
- Usage examples

### 3. Testing Strategy
- Unit testing for individual components
- Integration testing for workflows
- End-to-end testing for user scenarios
- Performance testing for scalability

---

**Related Documentation:**
- [API Documentation](api.md) - Detailed API reference
- [User Guide](user-guide.md) - Usage instructions
- [Configuration Guide](configuration.md) - Setup and configuration