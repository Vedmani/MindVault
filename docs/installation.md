# Installation Guide

This guide will walk you through installing MindVault and setting up all necessary dependencies.

## Prerequisites

### System Requirements

- **Python**: 3.12 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: At least 1GB free space for data storage

### External Dependencies

1. **MongoDB**: Required for data storage
   - [MongoDB Installation Guide](https://docs.mongodb.com/manual/installation/)
   - Alternatively, use MongoDB Atlas (cloud)

2. **Chromium Browser**: Required for web automation
   - Automatically installed with Playwright

## Installation Methods

### Method 1: Using pip (Recommended)

```bash
pip install mindvault
```

### Method 2: From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/mindvault.git
cd mindvault

# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

### Method 3: Using uv (Fast)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install mindvault
uv pip install mindvault
```

## Post-Installation Setup

### 1. Install Browser Dependencies

```bash
# Install Playwright browsers
playwright install chromium
```

### 2. Set Up MongoDB

#### Option A: Local MongoDB
```bash
# Ubuntu/Debian
sudo apt-get install mongodb

# macOS (using Homebrew)
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB service
sudo systemctl start mongod  # Linux
brew services start mongodb-community  # macOS
```

#### Option B: MongoDB Atlas (Cloud)
1. Create a free account at [MongoDB Atlas](https://cloud.mongodb.com/)
2. Create a new cluster
3. Get your connection string
4. Use it in your configuration

### 3. Configure Environment Variables

Create a `.env` file in your project directory:

```bash
# Copy the example environment file
cp .env.example .env
```

Edit the `.env` file with your credentials:

```env
# Twitter/X Authentication
TWITTER_CT0=your_ct0_cookie_here
TWITTER_AUTH_TOKEN=your_auth_token_here

# Optional: Separate scraper credentials
TWITTER_SCRAPER_CT0=your_scraper_ct0_cookie_here
TWITTER_SCRAPER_AUTH_TOKEN=your_scraper_auth_token_here

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
DB_NAME=mindvault

# Optional: Advanced Settings
LOG_LEVEL=INFO
MAX_CONCURRENT_DOWNLOADS=5
```

### 4. Verify Installation

```bash
# Test the installation
mindvault --version

# Run basic functionality test
python -c "import mindvault; print('MindVault installed successfully!')"
```

## Getting Twitter/X Credentials

### Method 1: Browser Developer Tools

1. **Open Twitter/X** in your browser
2. **Log in** to your account
3. **Open Developer Tools** (F12)
4. **Go to Application/Storage tab**
5. **Find Cookies** for twitter.com
6. **Copy the values** for:
   - `ct0` cookie
   - `auth_token` cookie

### Method 2: Browser Extension

You can use browser extensions like "Cookie Editor" to easily extract cookies.

## Directory Structure

After installation, MindVault will create the following structure in your home directory:

```
~/.mindvault/
├── twitter/
│   ├── bookmarks/
│   ├── tweet_ids/
│   ├── tweet_data/
│   ├── extracted_data/
│   ├── media/
│   ├── tweets.db
│   └── pending_tweets.json
└── logs/
```

## Troubleshooting

### Common Issues

#### 1. MongoDB Connection Error
```bash
# Check if MongoDB is running
sudo systemctl status mongod

# Start MongoDB if not running
sudo systemctl start mongod
```

#### 2. Python Version Issues
```bash
# Check Python version
python --version

# Install using specific Python version
python3.12 -m pip install mindvault
```

#### 3. Permission Errors
```bash
# Install in user directory
pip install --user mindvault

# Or use virtual environment
python -m venv mindvault-env
source mindvault-env/bin/activate  # Linux/macOS
mindvault-env\Scripts\activate     # Windows
pip install mindvault
```

#### 4. Playwright Browser Issues
```bash
# Reinstall Playwright browsers
playwright install --force chromium
```

### Getting Help

If you encounter issues:

1. **Check the logs**: `~/.mindvault/logs/`
2. **Read the FAQ**: [FAQ](faq.md)
3. **Search existing issues**: GitHub Issues
4. **Create a new issue**: Include error logs and system info

## Next Steps

After successful installation:

1. **Configure your settings**: See [Configuration Guide](configuration.md)
2. **Start using MindVault**: See [User Guide](user-guide.md)
3. **Explore the API**: See [API Documentation](api.md)

## Development Installation

For contributors and developers:

```bash
# Clone the repository
git clone https://github.com/yourusername/mindvault.git
cd mindvault

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

## Docker Installation (Coming Soon)

```bash
# Pull the Docker image
docker pull mindvault/mindvault:latest

# Run with docker-compose
docker-compose up -d
```

---

**Need help?** Check our [FAQ](faq.md) or [open an issue](https://github.com/yourusername/mindvault/issues).