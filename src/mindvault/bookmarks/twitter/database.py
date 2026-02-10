"""Database operations for the MindVault Twitter application.

This module handles database setup and tweet storage operations.
"""

from typing import Set, Optional
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, Column, String, DateTime
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from mindvault.core.config import settings
from mindvault.core.logger_setup import get_logger

logger = get_logger(__name__)

# Create base class for models
Base = declarative_base()

class Tweet(Base):
    """Model representing a tweet in the database.
    
    Attributes:
        tweet_id: Unique identifier of the tweet
        created_at: Timestamp when the record was created
    """
    
    __tablename__ = "tweet"
    
    tweet_id: str = Column(String, primary_key=True)
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Create engine and session factory
engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(bind=engine)

def create_database() -> None:
    """Create database and required tables."""
    logger.info("Creating database tables")
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully")

def get_db_session() -> Session:
    return SessionLocal()

def get_existing_tweet_ids() -> Set[str]:
    """Get set of tweet IDs already in the database.
    
    Returns:
        Set of tweet IDs as strings
    """
    logger.debug("Fetching existing tweet IDs from database")
    session = get_db_session()
    try:
        tweet_ids = set(id_[0] for id_ in session.query(Tweet.tweet_id).all())
    finally:
        session.close()
    logger.debug(f"Found {len(tweet_ids)} existing tweet IDs")
    return tweet_ids

def save_tweet_to_db(tweet_id: str) -> None:
    """Save a tweet record to the database.
    
    Args:
        tweet_id: ID of the tweet
        
    Raises:
        Exception: If saving to database fails
    """
    logger.debug(f"Saving tweet {tweet_id} to database")
    session = get_db_session()
    try:
        tweet = Tweet(
            tweet_id=tweet_id
        )
        session.add(tweet)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error while saving tweet {tweet_id}: {e}")
        raise
    finally:
        session.close()
    logger.debug(f"Successfully saved tweet {tweet_id}")

def get_total_tweets() -> int:
    """Get total number of tweets in the database.
    
    Returns:
        Total number of tweets
    """
    logger.debug("Counting total tweets in database")
    session = get_db_session()
    try:
        statement = text("SELECT COUNT(*) FROM tweet")
        count = session.execute(statement).scalar()
    finally:
        session.close()
    logger.debug(f"Total tweets in database: {count}")
    return count

def get_tweet_by_id(tweet_id: str) -> Optional[Tweet]:
    """Get a tweet record by its ID.
    
    Args:
        tweet_id: ID of the tweet to retrieve
        
    Returns:
        Tweet record if found, None otherwise
    """
    logger.debug(f"Fetching tweet {tweet_id} from database")
    session = get_db_session()
    try:
        tweet = session.query(Tweet).filter(Tweet.tweet_id == tweet_id).first()
    finally:
        session.close()
    if tweet:
        logger.debug(f"Found tweet {tweet_id}")
    else:
        logger.debug(f"Tweet {tweet_id} not found")
    return tweet
    
if __name__ == "__main__":
    logger.info("Initializing database")
    create_database()
    logger.info("Database initialization completed")