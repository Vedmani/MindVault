from typing import List, Optional, Any, Dict, Literal, Tuple, Union
from pydantic import BaseModel
import json
from pathlib import Path
from enum import Enum
from mindvault.core.logger_setup import get_logger
from mindvault.bookmarks.twitter.schema import (
    ThreadedConversationWithInjectionsV2,
    ItemContent,
    ItemContentInThread,
    TweetTombstone,
    TweetData,
    Media,
    Article,
    ArticleMediaEntity,
)
from mindvault.core.config import settings
import uuid

# TODO: Extract the size of the media files as well. (Video is done, image is not.)
# TODO: Figure out why extraction is failing for some tweets, specifically 1675598137291857921, 1778153659106533806, 1701651611431379142, 1838250093113221522, 1663653644951076864
# TODO: There might be something wrong with the card data extraction.

logger = get_logger(__name__)


def _extract_article_content(article: Article) -> Tuple[str, List[ArticleMediaEntity]]:
    """Extract text content from a Twitter Article with inline media placeholders.

    Args:
        article: The Article object from a tweet

    Returns:
        Tuple of (extracted_text, list_of_media_entities)
    """
    article_data = article.article_results.result
    content_state = article_data.content_state

    if content_state is None:
        # Fallback to preview_text if no content_state
        return article_data.title + "\n\n" + (article_data.preview_text or ""), []

    # Build entity map lookup: key -> media_id
    entity_map: Dict[str, str] = {}
    for entity_item in content_state.entityMap:
        key = entity_item.key
        value = entity_item.value
        if value.get("type") == "MEDIA":
            media_items = value.get("data", {}).get("mediaItems", [])
            if media_items:
                # Use the first media item's media_id
                entity_map[key] = media_items[0].get("mediaId", "")

    # Build media_id -> url lookup from media_entities
    media_id_to_url: Dict[str, str] = {}
    for me in article_data.media_entities:
        if me.media_info:
            if me.media_info.is_image() and me.media_info.original_img_url:
                media_id_to_url[me.media_id] = me.media_info.original_img_url
            elif me.media_info.is_video() and me.media_info.preview_image:
                # For videos, use preview/thumbnail URL in text placeholder
                media_id_to_url[me.media_id] = (
                    me.media_info.preview_image.original_img_url
                )

    # Process blocks to build text
    text_parts = []

    # Add title first
    text_parts.append(f"# {article_data.title}")
    text_parts.append("")  # Empty line after title

    for block in content_state.blocks:
        block_type = block.type
        block_text = block.text.strip()

        if block_type == "atomic":
            # Atomic blocks can be: MEDIA, MARKDOWN, DIVIDER, or TWEET
            if block.entityRanges:
                entity_key = str(block.entityRanges[0].get("key", ""))

                # Find the entity to determine its type
                entity_item = next(
                    (e for e in content_state.entityMap if e.key == entity_key), None
                )

                if entity_item:
                    entity_type = entity_item.value.get("type", "")

                    if entity_type == "MEDIA":
                        # This is actual media (image/video)
                        media_id = entity_map.get(entity_key, "")
                        media_url = media_id_to_url.get(media_id, "")
                        if media_url:
                            text_parts.append(f"![Media]({media_url})")
                        else:
                            text_parts.append("![Media](unknown)")

                    elif entity_type == "MARKDOWN":
                        # This is a code snippet/markdown block
                        markdown_content = entity_item.value.get("data", {}).get(
                            "markdown", ""
                        )
                        if markdown_content:
                            text_parts.append(f"\n{markdown_content}\n")
                        else:
                            text_parts.append("[CODE SNIPPET]")

                    elif entity_type == "DIVIDER":
                        # This is a horizontal divider
                        text_parts.append("\n---\n")

                    elif entity_type == "TWEET":
                        # This is an embedded tweet
                        tweet_id = entity_item.value.get("data", {}).get("tweetId", "")
                        if tweet_id:
                            text_parts.append(
                                f"[Embedded Tweet: https://x.com/i/status/{tweet_id}]"
                            )
                        else:
                            text_parts.append("[Embedded Tweet]")

                    else:
                        # Unknown atomic type
                        text_parts.append(f"[{entity_type}]")
                else:
                    text_parts.append("[UNKNOWN ELEMENT]")
        elif block_type == "header-one":
            text_parts.append(f"# {block_text}")
        elif block_type == "header-two":
            text_parts.append(f"## {block_text}")
        elif block_type == "header-three":
            text_parts.append(f"### {block_text}")
        elif block_type == "unordered-list-item":
            text_parts.append(f"• {block_text}")
        elif block_type == "ordered-list-item":
            text_parts.append(f"- {block_text}")
        elif block_type == "blockquote":
            text_parts.append(f"> {block_text}")
        else:
            # Handle unstyled and other block types - just add the text
            if block_text:
                text_parts.append(block_text)

    return "\n".join(text_parts), article_data.media_entities


class ExtractedMedia(BaseModel):
    tweet_id: str
    media_id: str
    media_url: str
    thumbnail_url: Optional[str] = None
    media_type: Literal["image", "video", "animated_gif", "card_image"]
    media_duration: Optional[int] = None
    text: Optional[str] = None


class ExtractedMediaList(BaseModel):
    media: List[ExtractedMedia]


class MediaUrlHandling(Enum):
    """How to handle media URLs in tweet text."""

    KEEP = "keep"  # Keep the original shortened URLs in text
    REPLACE = "replace"  # Replace shortened URLs with expanded versions
    REMOVE = "remove"  # Remove media URLs from text entirely


# Pydantic models for the extracted information.


class ExtractedQuote(BaseModel):
    id: str  # Tweet ID of the quoted tweet
    text: str
    username: str  # Twitter handle (screen name)
    actual_name: str  # The tweet author's full name
    link: Optional[str] = None
    urls: List[str] = []  # All URLs extracted from the quoted tweet's text
    media_urls: List[
        str
    ] = []  # Media URLs from the quoted tweet (e.g. image or video links)
    video_durations: Dict[
        str, float
    ] = {}  # Video durations in seconds, keyed by media URL
    created_at: str  # When the quoted tweet was created
    hashtags: List[str] = []  # Hashtags used in the tweet
    mentions: List[str] = []  # User mentions in the tweet (@username)
    media: List[Media] = []


class ExtractedCardImage(BaseModel):
    alt: str
    url: str
    width: int
    height: int


class ExtractedCard(BaseModel):
    """Only essential content-related information from Twitter cards"""

    title: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    url: Optional[str] = None  # The actual destination URL
    images: List[ExtractedCardImage] = []  # Add this field to store card images


class ExtractedTweet(BaseModel):
    id: str
    text: str
    username: str  # Twitter handle (screen name)
    actual_name: str  # The tweet author's full name
    favourite_count: int
    reply_count: int
    retweet_count: int
    urls: List[str] = []  # URLs mentioned in the tweet text
    media_urls: List[str] = []  # URLs to tweet media (images, videos)
    video_durations: Dict[
        str, float
    ] = {}  # Video durations in seconds, keyed by media URL
    created_at: str  # When the tweet was created
    quoted_tweet: Optional[ExtractedQuote] = None
    card: Optional[ExtractedCard] = None
    hashtags: List[str] = []  # Hashtags used in the tweet
    mentions: List[str] = []  # User mentions in the tweet (@username)
    media: List[Media]
    article_media: List[ArticleMediaEntity] = []  # Media entities from Twitter Articles


class ExtractedConversation(BaseModel):
    main_tweet: ExtractedTweet
    replies: List[ExtractedTweet] = []


class ExtractedTweetWithMedia(ExtractedTweet):
    extracted_media: List[ExtractedMedia]


class ExtractedConversationWithMedia(ExtractedConversation):
    main_tweet: ExtractedTweetWithMedia
    replies: List[ExtractedTweetWithMedia] = []


def replace_urls_in_text(text: str, entities: Any) -> str:
    """Replace shortened URLs in text with their expanded versions."""
    if not hasattr(entities, "urls") or not entities.urls:
        return text

    # Sort URLs by their position in reverse order to avoid messing up the indices
    urls = sorted(entities.urls, key=lambda x: x.indices[0], reverse=True)

    # Replace each shortened URL with its expanded version
    for url in urls:
        start, end = url.indices
        text = text[:start] + url.expanded_url + text[end:]

    return text


def handle_media_urls_in_text(
    text: str, entities: Any, handling: MediaUrlHandling = MediaUrlHandling.KEEP
) -> str:
    """Handle media URLs in text based on the specified handling option.

    Args:
        text: The tweet text to process
        entities: Tweet entities containing media information
        handling: How to handle media URLs (keep/replace/remove)

    Returns:
        Processed text with media URLs handled according to the specified option
    """
    if not hasattr(entities, "media") or not entities.media:
        return text

    # Sort media by their position in reverse order to avoid messing up the indices
    media_items = sorted(entities.media, key=lambda x: x.indices[0], reverse=True)

    # Handle media URLs based on the specified option
    for media in media_items:
        start, end = media.indices
        if handling == MediaUrlHandling.KEEP:
            continue  # Keep original text
        elif handling == MediaUrlHandling.REPLACE:
            text = text[:start] + media.expanded_url + text[end:]
        elif handling == MediaUrlHandling.REMOVE:
            text = text[:start] + text[end:]

    return text


# Helper function to extract the essential data from a tweet contained in an ItemContent
def extract_tweet_data(
    item_content: Union[ItemContent, ItemContentInThread],
    media_url_handling: MediaUrlHandling = MediaUrlHandling.KEEP,
) -> ExtractedTweet:
    # Fallback if no tweet_results or empty tweet_results (result is None)
    if item_content.tweet_results is None or item_content.tweet_results.result is None:
        return ExtractedTweet(
            id="",
            text="[No tweet text available]",
            username="",
            actual_name="",
            favourite_count=0,
            reply_count=0,
            retweet_count=0,
            urls=[],
            media_urls=[],
            video_durations={},
            created_at="",
            hashtags=[],
            mentions=[],
            media=[],
        )
    tweet_result = item_content.tweet_results
    result = tweet_result.result

    # If tweet marked as tombstone, return a placeholder.
    if isinstance(result, TweetTombstone):
        return ExtractedTweet(
            id="",
            text="[Tweet unavailable]",
            username="",
            actual_name="",
            favourite_count=0,
            reply_count=0,
            retweet_count=0,
            urls=[],
            media_urls=[],
            video_durations={},
            created_at="",
            hashtags=[],
            mentions=[],
            media=[],
        )

    # Determine the tweet object from result. (It may be wrapped in a TweetWithVisibilityResult.)
    tweet_obj = (
        result.tweet
        if hasattr(result, "tweet")
        else (
            result
            if not isinstance(result, TweetTombstone) and hasattr(result, "legacy")
            else None
        )
    )
    if tweet_obj is None:
        return ExtractedTweet(
            id="",
            text="[Unknown tweet format]",
            username="",
            actual_name="",
            favourite_count=0,
            reply_count=0,
            retweet_count=0,
            urls=[],
            media_urls=[],
            video_durations={},
            created_at="",
            hashtags=[],
            mentions=[],
            media=[],
        )

    # Get tweet id.
    tweet_id = tweet_obj.rest_id

    # Get username (screen name) and actual name (from legacy.name) using helper methods on Core.
    username = (
        tweet_obj.core.get_screen_name()
        if hasattr(tweet_obj, "core")
        else "Unknown User"
    )
    actual_name = (
        tweet_obj.core.get_user_name() if hasattr(tweet_obj, "core") else "Unknown Name"
    )

    # Variable to hold article media entities if this is an article tweet
    article_media_entities: List[ArticleMediaEntity] = []

    # Determine the tweet text - check for article first, then note_tweet, then legacy
    if hasattr(tweet_obj, "article") and tweet_obj.article is not None:
        # This is an article tweet - extract article content with media placeholders
        text, article_media_entities = _extract_article_content(tweet_obj.article)
        logger.info(
            f"Extracted article tweet {tweet_id} with {len(article_media_entities)} media entities"
        )
    elif tweet_obj.note_tweet is not None:
        text = tweet_obj.note_tweet.note_tweet_results.result.text
        # Replace URLs in note tweet text if entities exist in note_tweet
        if hasattr(tweet_obj.note_tweet.note_tweet_results.result, "entity_set"):
            text = replace_urls_in_text(
                text, tweet_obj.note_tweet.note_tweet_results.result.entity_set
            )
    else:
        text = (
            tweet_obj.legacy.full_text.strip()
            if hasattr(tweet_obj, "legacy") and tweet_obj.legacy
            else ""
        )
        # Replace URLs in legacy tweet text
        if (
            hasattr(tweet_obj, "legacy")
            and tweet_obj.legacy
            and hasattr(tweet_obj.legacy, "entities")
        ):
            text = replace_urls_in_text(text, tweet_obj.legacy.entities)

    # Extract counts.
    fav_count = (
        tweet_obj.legacy.favorite_count
        if hasattr(tweet_obj, "legacy")
        and tweet_obj.legacy
        and hasattr(tweet_obj.legacy, "favorite_count")
        else 0
    )
    reply_count = (
        tweet_obj.legacy.reply_count
        if hasattr(tweet_obj, "legacy")
        and tweet_obj.legacy
        and hasattr(tweet_obj.legacy, "reply_count")
        else 0
    )
    retweet_count = (
        tweet_obj.legacy.retweet_count
        if hasattr(tweet_obj, "legacy")
        and tweet_obj.legacy
        and hasattr(tweet_obj.legacy, "retweet_count")
        else 0
    )

    # Extract URLs from tweet entities.
    urls = []
    hashtags = []
    mentions = []
    media_list = []  # List to store Media objects
    if (
        hasattr(tweet_obj, "legacy")
        and tweet_obj.legacy
        and hasattr(tweet_obj.legacy, "entities")
        and tweet_obj.legacy.entities
    ):
        entities = tweet_obj.legacy.entities
        if getattr(entities, "urls", None):
            for url_obj in entities.urls:
                urls.append(url_obj.expanded_url)
        if getattr(entities, "hashtags", None):
            for hashtag in entities.hashtags:
                if hasattr(hashtag, "text"):
                    hashtags.append(hashtag.text)
        if entities.user_mentions:
            mentions = [mention.screen_name for mention in entities.user_mentions]
        # Extract media objects directly
        if getattr(entities, "media", None):
            media_list.extend(entities.media)

    # Extract media URLs and video durations from tweet entities and handle them in text
    media_urls = []
    video_durations = {}
    if (
        hasattr(tweet_obj, "legacy")
        and tweet_obj.legacy
        and hasattr(tweet_obj.legacy, "entities")
        and tweet_obj.legacy.entities
    ):
        entities = tweet_obj.legacy.entities
        if getattr(entities, "media", None):
            # First collect media URLs and video durations
            for media in entities.media:
                media_urls.append(media.expanded_url)
                # If it's a video, extract its duration
                if media.type == "video" and hasattr(media, "video_info"):
                    duration_millis = media.video_info.duration_millis
                    if duration_millis is not None:
                        video_durations[media.expanded_url] = (
                            duration_millis / 1000.0
                        )  # Convert to seconds
            # Then handle media URLs in text according to preference
            text = handle_media_urls_in_text(text, entities, media_url_handling)

    # Get creation date
    created_at = (
        tweet_obj.legacy.created_at
        if hasattr(tweet_obj, "legacy")
        and tweet_obj.legacy
        and hasattr(tweet_obj.legacy, "created_at")
        else ""
    )

    # Extract quoted tweet if available.
    quoted = None
    if tweet_obj.quoted_status_result and tweet_obj.quoted_status_result.result:
        quoted_obj = tweet_obj.quoted_status_result.result

        # Skip if the quoted tweet is a tombstone
        if isinstance(quoted_obj, TweetTombstone):
            # Create a basic quoted tweet with minimal information
            quoted = ExtractedQuote(
                id="",
                text="[Quoted tweet unavailable]",
                username="",
                actual_name="",
                created_at="",
            )
        else:
            if hasattr(quoted_obj, "tweet"):
                quoted_obj = quoted_obj.tweet

            # Extract quoted tweet ID
            quoted_id = quoted_obj.rest_id if hasattr(quoted_obj, "rest_id") else ""

            # Check for note_tweet in quoted tweet
            if hasattr(quoted_obj, "note_tweet") and quoted_obj.note_tweet is not None:
                quoted_text = quoted_obj.note_tweet.note_tweet_results.result.text
                # Replace URLs in quoted note tweet text
                if hasattr(
                    quoted_obj.note_tweet.note_tweet_results.result, "entity_set"
                ):
                    quoted_text = replace_urls_in_text(
                        quoted_text,
                        quoted_obj.note_tweet.note_tweet_results.result.entity_set,
                    )
            else:
                quoted_text = (
                    quoted_obj.legacy.full_text.strip()
                    if hasattr(quoted_obj, "legacy") and quoted_obj.legacy
                    else ""
                )
                # Replace URLs in quoted legacy tweet text
                if (
                    hasattr(quoted_obj, "legacy")
                    and quoted_obj.legacy
                    and hasattr(quoted_obj.legacy, "entities")
                ):
                    quoted_text = replace_urls_in_text(
                        quoted_text, quoted_obj.legacy.entities
                    )

            quoted_username = (
                quoted_obj.core.get_screen_name()
                if hasattr(quoted_obj, "core")
                else "Unknown User"
            )
            quoted_actual_name = (
                quoted_obj.core.get_user_name()
                if hasattr(quoted_obj, "core")
                else "Unknown Name"
            )
            quoted_created_at = (
                quoted_obj.legacy.created_at
                if hasattr(quoted_obj, "legacy")
                and quoted_obj.legacy
                and hasattr(quoted_obj.legacy, "created_at")
                else ""
            )
            quoted_link = (
                tweet_obj.legacy.quoted_status_permalink.expanded
                if hasattr(tweet_obj, "legacy")
                and tweet_obj.legacy
                and hasattr(tweet_obj.legacy, "quoted_status_permalink")
                and tweet_obj.legacy.quoted_status_permalink
                else None
            )
            quoted_urls = []
            quoted_media_urls = []
            quoted_video_durations = {}
            quoted_hashtags = []
            quoted_mentions = []
            quoted_media_list = []  # List to store Media objects for quoted tweet
            if (
                hasattr(quoted_obj, "legacy")
                and quoted_obj.legacy
                and quoted_obj.legacy.entities
            ):
                q_entities = quoted_obj.legacy.entities
                if getattr(q_entities, "urls", None):
                    for url_obj in q_entities.urls:
                        quoted_urls.append(url_obj.expanded_url)
                if getattr(q_entities, "media", None):
                    # Extract media objects directly
                    quoted_media_list.extend(q_entities.media)
                    for media in q_entities.media:
                        quoted_media_urls.append(media.expanded_url)
                        # If it's a video, extract its duration
                        if media.type == "video" and hasattr(media, "video_info"):
                            duration_millis = media.video_info.duration_millis
                            if duration_millis is not None:
                                quoted_video_durations[media.expanded_url] = (
                                    duration_millis / 1000.0
                                )  # Convert to seconds
                    # Handle media URLs in quoted text according to preference
                    quoted_text = handle_media_urls_in_text(
                        quoted_text, q_entities, media_url_handling
                    )
                if getattr(q_entities, "hashtags", None):
                    for hashtag in q_entities.hashtags:
                        if hasattr(hashtag, "text"):
                            quoted_hashtags.append(hashtag.text)
                if getattr(q_entities, "user_mentions", None):
                    for mention in q_entities.user_mentions:
                        if hasattr(mention, "screen_name"):
                            quoted_mentions.append(mention.screen_name)
            quoted_created_at = (
                quoted_obj.legacy.created_at
                if hasattr(quoted_obj, "legacy")
                and quoted_obj.legacy
                and hasattr(quoted_obj.legacy, "created_at")
                else ""
            )
            # We combine the URLs from the text field and media.
            quoted = ExtractedQuote(
                id=quoted_id,
                text=quoted_text,
                username=quoted_username,
                actual_name=quoted_actual_name,
                link=quoted_link,
                urls=quoted_urls,
                media_urls=quoted_media_urls,
                video_durations=quoted_video_durations,
                created_at=quoted_created_at,
                hashtags=quoted_hashtags,
                mentions=quoted_mentions,
                media=quoted_media_list,  # Add the extracted media list to the ExtractedQuote
            )

    # Extract card data
    card = None
    if tweet_obj and hasattr(tweet_obj, "card"):
        card = _extract_card_data(tweet_obj)

    return ExtractedTweet(
        id=tweet_id,
        text=text,
        username=username,
        actual_name=actual_name,
        favourite_count=fav_count,
        reply_count=reply_count,
        retweet_count=retweet_count,
        urls=urls,
        media_urls=media_urls,
        video_durations=video_durations,
        created_at=created_at,
        quoted_tweet=quoted,
        card=card,
        hashtags=hashtags,
        mentions=mentions,
        media=media_list,
        article_media=article_media_entities,  # Add article media entities
    )


# Main extractor function: given a ThreadedConversationWithInjectionsV2, extract the conversation.
def _extract_conversation(
    convo: ThreadedConversationWithInjectionsV2,
    media_url_handling: MediaUrlHandling = MediaUrlHandling.KEEP,
) -> ExtractedConversation:
    main_tweet = None
    replies = []
    # Iterate over all instructions.
    for instruction in convo.instructions:
        if instruction.type != "TimelineAddEntries" or not instruction.entries:
            continue
        for entry in instruction.entries:
            # Skip entries starting with "tweetdetailrelatedtweets" or "cursor"
            if entry.entryId.startswith(
                ("tweetdetailrelatedtweets", "cursor")
            ):  # These are related tweets which are recommended by twitter and are not part of the conversation and cursor entries caused by scrolling or pagination.
                continue
            if (
                entry.entry_type == "main_tweet"
                and entry.content
                and entry.content.itemContent
            ):
                main_tweet = extract_tweet_data(
                    entry.content.itemContent, media_url_handling
                )
            elif entry.entry_type == "conversation":
                if entry.content.items:
                    for item in entry.content.items:
                        if (
                            item
                            and item.item
                            and item.item.itemContent
                            and item.item.itemContent.tweet_results
                        ):
                            replies.append(
                                extract_tweet_data(
                                    item.item.itemContent, media_url_handling
                                )
                            )
                elif entry.content.itemContent:
                    replies.append(
                        extract_tweet_data(
                            entry.content.itemContent, media_url_handling
                        )
                    )
    if main_tweet is None:
        raise ValueError("No main tweet found in conversation data")
    return ExtractedConversation(main_tweet=main_tweet, replies=replies)


# Add this helper function to extract card data
def _extract_card_data(tweet_obj: Any) -> Optional[ExtractedCard]:
    """Extract only essential content information from a tweet's card."""
    if not hasattr(tweet_obj, "card") or tweet_obj.card is None:
        return None

    card = tweet_obj.card
    card_data = {
        "images": []  # Initialize empty list for images
    }

    # Process binding values to extract content-related fields and images
    if hasattr(card.legacy, "binding_values"):
        for binding in card.legacy.binding_values:
            key = binding.key
            value = binding.value

            if key == "title":
                card_data["title"] = value.get("string_value")
            elif key == "description":
                card_data["description"] = value.get("string_value")
            elif key == "domain":
                card_data["domain"] = value.get("string_value")
            elif key == "card_url":
                card_data["url"] = value.get("string_value")
            # Extract image data
            elif key == "photo_image_full_size_original":
                img_value = value.get("image_value", {})
                if img_value and "url" in img_value:
                    card_data["images"].append(
                        ExtractedCardImage(
                            url=img_value["url"],
                            width=img_value.get("width", 0),
                            height=img_value.get("height", 0),
                            alt=img_value.get("alt", ""),
                        )
                    )

    # Only return card data if we have at least one content field or image
    if any(v for k, v in card_data.items() if k != "images") or card_data["images"]:
        return ExtractedCard(**card_data)
    return None


def process_single_tweet_file(
    json_file: Path,
    output_dir: Optional[Path] = None,
    save_to_file: bool = False,
    media_url_handling: MediaUrlHandling = MediaUrlHandling.KEEP,
) -> Optional[ExtractedConversation]:
    """Process a single tweet JSON file and extract conversation.

    Args:
        json_file: Path to the JSON file containing tweet data
        output_dir: Directory to save extracted conversation if save_to_file is True
        save_to_file: Whether to save the extracted data to a file
        media_url_handling: How to handle media URLs in tweet text (keep/replace/remove)

    Returns:
        ExtractedConversation if successful, None if processing failed

    Raises:
        FileNotFoundError: If the input file doesn't exist
        ValueError: If save_to_file is True but output_dir is None
    """
    if save_to_file and output_dir is None:
        raise ValueError("output_dir must be provided when save_to_file is True")

    try:
        # Extract tweet ID from filename
        tweet_id = json_file.stem

        # Load and process tweet data
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        tweet_data = TweetData.model_validate(data)
        extracted_conv = _extract_conversation(
            tweet_data.threaded_conversation_with_injections_v2, media_url_handling
        )

        # Save to file if requested
        if save_to_file:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{tweet_id}_extracted.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(extracted_conv.model_dump(), f, indent=2)
            logger.info(f"Saved extracted data for tweet {tweet_id}")

        return extracted_conv

    except Exception as e:
        logger.error(f"Error processing {json_file.name}: {e}")
        return None


def process_all_tweet_files(
    tweet_data_dir: Path,
    output_dir: Path,
    media_url_handling: MediaUrlHandling = MediaUrlHandling.KEEP,
) -> None:
    """Process all tweet JSON files in the specified directory and extract conversations.

    Args:
        tweet_data_dir: Directory containing tweet JSON files
        output_dir: Directory to save extracted conversations
        media_url_handling: How to handle media URLs in tweet text (keep/replace/remove)
    """
    # Get all JSON files in the tweet_data directory
    json_files = list(tweet_data_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} tweet files to process")

    processed = 0
    failed = 0
    failed_tweets = []

    for json_file in json_files:
        # Skip if already processed
        tweet_id = json_file.stem
        output_file = output_dir / f"{tweet_id}_extracted.json"

        try:
            # Try to read existing file to check if processing is complete
            with open(output_file, "r") as f:
                json.load(f)  # If this succeeds, file exists and is valid JSON
            logger.info(f"Skipping {tweet_id} - already processed")
            continue
        except (FileNotFoundError, json.JSONDecodeError):
            # File doesn't exist or is corrupted, proceed with processing
            pass

        # Process the file
        result = process_single_tweet_file(
            json_file,
            output_dir,
            save_to_file=True,
            media_url_handling=media_url_handling,
        )
        if result is not None:
            processed += 1
        else:
            failed += 1
            failed_tweets.append(tweet_id)
            logger.error(f"Failed to process tweet: {tweet_id}")

    logger.info(f"Processing complete. Processed: {processed}, Failed: {failed}")
    if failed_tweets:
        logger.info("Failed tweets:")
        for tweet_id in failed_tweets:
            logger.info(f"- {tweet_id}")


def _process_video_media(
    tweet_id: str,
    media_id: str,
    media_url: str,
    duration_millis: Optional[int],
    video_type: str,
    thumbnail_url: Optional[str],
    video_length_limit: Optional[int] = 30,
) -> Optional[ExtractedMedia]:
    """
    Process video media with duration check and bitrate selection.

    Args:
        tweet_id: ID of the tweet containing this video
        media_id: ID of the media
        media_url: Direct URL to the video (highest bitrate variant)
        duration_millis: Video duration in milliseconds
        video_type: Type of video ("video" or "animated_gif")
        thumbnail_url: Optional thumbnail URL
        video_length_limit: Optional video length limit in seconds

    Returns:
        ExtractedMedia object if video passes length filter, None otherwise
    """
    # Calculate duration in seconds
    if duration_millis is not None:
        video_duration = round(duration_millis / 1000)
    else:
        video_duration = 0

    # Skip videos that exceed length limit
    if video_length_limit is not None and video_duration > video_length_limit:
        logger.info(
            f"Skipping video {media_id} in tweet {tweet_id} with duration "
            f"{video_duration}s (exceeds limit of {video_length_limit}s)"
        )
        return None

    return ExtractedMedia(
        tweet_id=tweet_id,
        media_id=media_id,
        media_url=media_url,
        thumbnail_url=thumbnail_url,
        media_type=video_type,
        media_duration=video_duration,
    )


def extract_media_info_from_tweet(
    tweet: ExtractedTweet,
    extract_video_thumbnail: bool = False,
    extract_videos: bool = True,
    extract_images: bool = True,
    extract_card_images: bool = True,
    video_length_limit: Optional[int] = 30,
) -> ExtractedMediaList:
    """Extract media information from a tweet and return a list of DownloadMedia objects.
    For videos, the highest bitrate variant is chosen.
    Also processes media from quoted tweets and card images if present.

    Args:
        tweet: The ExtractedTweet object containing media information
        extract_video_thumbnail: Whether to include thumbnail URLs for videos
        extract_videos: Whether to extract videos and animated GIFs
        extract_images: Whether to extract images
        extract_card_images: Whether to extract images from Twitter cards
        video_length_limit: Optional video length limit in seconds. If None, all videos are extracted regardless of length.
    """
    media_list = []

    # Helper function to process media from a tweet or quoted tweet
    def process_media(tweet_obj, tweet_id):
        for media in tweet_obj.media:
            if media.type == "photo" and extract_images:
                _media = ExtractedMedia(
                    tweet_id=tweet_id,
                    media_id=media.id_str,
                    media_url=media.media_url_https + "?name=orig",
                    media_type="image",
                )
                media_list.append(_media)
            elif (
                media.type == "video" or media.type == "animated_gif"
            ) and extract_videos:
                if not media.video_info or not media.video_info.variants:
                    continue

                # Select highest bitrate variant
                sorted_variants = sorted(
                    media.video_info.variants,
                    key=lambda x: x.bitrate if x.bitrate is not None else 0,
                    reverse=True,
                )

                _video = _process_video_media(
                    tweet_id=tweet_id,
                    media_id=media.id_str,
                    media_url=sorted_variants[0].url,
                    duration_millis=media.video_info.duration_millis,
                    video_type=media.type,
                    thumbnail_url=media.media_url_https + "?name=orig"
                    if extract_video_thumbnail
                    else None,
                    video_length_limit=video_length_limit,
                )

                if _video:
                    media_list.append(_video)

        # Process card images if the tweet has a card
        if extract_card_images and hasattr(tweet_obj, "card") and tweet_obj.card:
            if hasattr(tweet_obj.card, "images") and tweet_obj.card.images:
                for image in tweet_obj.card.images:
                    _media = ExtractedMedia(
                        tweet_id=tweet_id,
                        media_id=str(uuid.uuid4()).split("-")[0],
                        media_url=image.url,
                        media_type="card_image",
                    )
                    media_list.append(_media)

    # Process media from the main tweet
    process_media(tweet, tweet.id)

    # Process media from quoted tweet if it exists
    if (
        tweet.quoted_tweet
        and hasattr(tweet.quoted_tweet, "media")
        and tweet.quoted_tweet.media
    ):
        process_media(tweet.quoted_tweet, tweet.quoted_tweet.id)

    # Process article media if present (from Twitter Articles)
    if hasattr(tweet, "article_media") and tweet.article_media:
        for article_me in tweet.article_media:
            media_info = article_me.media_info

            # Handle article images
            if media_info.is_image() and extract_images:
                if media_info.original_img_url:
                    _media = ExtractedMedia(
                        tweet_id=tweet.id,
                        media_id=article_me.media_id,
                        media_url=media_info.original_img_url,
                        media_type="image",
                    )
                    media_list.append(_media)

            # Handle article videos
            elif media_info.is_video() and extract_videos:
                if not media_info.variants:
                    continue

                # Select highest bitrate variant
                sorted_variants = sorted(
                    media_info.variants,
                    key=lambda x: x.bitrate if x.bitrate is not None else 0,
                    reverse=True,
                )

                _video = _process_video_media(
                    tweet_id=tweet.id,
                    media_id=article_me.media_id,
                    media_url=sorted_variants[0].url,
                    duration_millis=media_info.duration_millis,
                    video_type="video",
                    thumbnail_url=media_info.preview_image.original_img_url
                    if extract_video_thumbnail and media_info.preview_image
                    else None,
                    video_length_limit=video_length_limit,
                )

                if _video:
                    media_list.append(_video)

    return ExtractedMediaList(media=media_list)


def extract_media_info_from_conversation(
    conversation: ExtractedConversation,
    extract_video_thumbnail: bool = False,
    extract_videos: bool = True,
    extract_images: bool = True,
    extract_card_images: bool = True,
    video_length_limit: Optional[int] = 30,
) -> ExtractedMediaList:
    """Extract media information from a conversation and return a list of DownloadMedia objects.

    Args:
        conversation: The ExtractedConversation object containing tweets
        extract_video_thumbnail: Whether to include thumbnail URLs for videos
        extract_videos: Whether to extract videos and animated GIFs
        extract_images: Whether to extract images
        extract_card_images: Whether to extract images from Twitter cards
        video_length_limit: Optional video length limit in seconds. If None, all videos are extracted regardless of length.
    """
    media_list = []
    media_list.extend(
        extract_media_info_from_tweet(
            conversation.main_tweet,
            extract_video_thumbnail,
            extract_videos,
            extract_images,
            extract_card_images,
            video_length_limit,
        ).media
    )

    for tweet in conversation.replies:
        media_list.extend(
            extract_media_info_from_tweet(
                tweet,
                extract_video_thumbnail,
                extract_videos,
                extract_images,
                extract_card_images,
                video_length_limit,
            ).media
        )

    return ExtractedMediaList(media=media_list)


def convert_tweet_to_tweet_with_media(
    tweet: ExtractedTweet,
    extract_video_thumbnail: bool = False,
    extract_videos: bool = True,
    extract_images: bool = True,
    extract_card_images: bool = True,
    video_length_limit: Optional[int] = None,
) -> ExtractedTweetWithMedia:
    """Convert an ExtractedTweet to ExtractedTweetWithMedia by extracting media information.

    Args:
        tweet: The ExtractedTweet to convert
        extract_video_thumbnail: Whether to include thumbnail URLs for videos
        extract_videos: Whether to extract videos and animated GIFs
        extract_images: Whether to extract images
        extract_card_images: Whether to extract images from Twitter cards
        video_length_limit: Optional video length limit in seconds

    Returns:
        ExtractedTweetWithMedia with the same tweet data plus extracted media
    """
    # Extract media information from the tweet
    media_list = extract_media_info_from_tweet(
        tweet,
        extract_video_thumbnail,
        extract_videos,
        extract_images,
        extract_card_images,
        video_length_limit,
    ).media

    # Create a new ExtractedTweetWithMedia with the same data plus media
    tweet_dict = tweet.model_dump()
    tweet_dict["extracted_media"] = media_list

    return ExtractedTweetWithMedia(**tweet_dict)


def _convert_conversation_to_conversation_with_media(
    conversation: ExtractedConversation,
    extract_video_thumbnail: bool = False,
    extract_videos: bool = True,
    extract_images: bool = True,
    extract_card_images: bool = True,
    video_length_limit: Optional[int] = None,
) -> ExtractedConversationWithMedia:
    """Convert an ExtractedConversation to ExtractedConversationWithMedia by extracting media information.

    Args:
        conversation: The ExtractedConversation to convert
        extract_video_thumbnail: Whether to include thumbnail URLs for videos
        extract_videos: Whether to extract videos and animated GIFs
        extract_images: Whether to extract images
        extract_card_images: Whether to extract images from Twitter cards
        video_length_limit: Optional video length limit in seconds

    Returns:
        ExtractedConversationWithMedia with the same conversation data plus extracted media
    """
    # Convert main tweet to ExtractedTweetWithMedia
    main_tweet_with_media = convert_tweet_to_tweet_with_media(
        conversation.main_tweet,
        extract_video_thumbnail,
        extract_videos,
        extract_images,
        extract_card_images,
        video_length_limit,
    )

    # Convert all reply tweets to ExtractedTweetWithMedia
    replies_with_media = [
        convert_tweet_to_tweet_with_media(
            reply,
            extract_video_thumbnail,
            extract_videos,
            extract_images,
            extract_card_images,
            video_length_limit,
        )
        for reply in conversation.replies
    ]

    # Create and return the ExtractedConversationWithMedia
    return ExtractedConversationWithMedia(
        main_tweet=main_tweet_with_media, replies=replies_with_media
    )


def process_single_tweet_file_with_media(
    json_file: Path,
    output_dir: Optional[Path] = None,
    save_to_file: bool = False,
    media_url_handling: MediaUrlHandling = MediaUrlHandling.KEEP,
    extract_video_thumbnail: bool = False,
    extract_videos: bool = True,
    extract_images: bool = True,
    extract_card_images: bool = True,
    video_length_limit: Optional[int] = None,
) -> Optional[ExtractedConversationWithMedia]:
    """Process a single tweet JSON file and extract conversation with media.

    Args:
        json_file: Path to the JSON file containing tweet data
        output_dir: Directory to save extracted conversation if save_to_file is True
        save_to_file: Whether to save the extracted data to a file
        media_url_handling: How to handle media URLs in tweet text (keep/replace/remove)
        extract_video_thumbnail: Whether to include thumbnail URLs for videos
        extract_videos: Whether to extract videos and animated GIFs
        extract_images: Whether to extract images
        extract_card_images: Whether to extract images from Twitter cards
        video_length_limit: Optional video length limit in seconds

    Returns:
        ExtractedConversationWithMedia if successful, None if processing failed
    """
    try:
        # First extract the conversation using the existing function
        conversation = process_single_tweet_file(
            json_file,
            output_dir=None,  # Don't save the intermediate result
            save_to_file=False,
            media_url_handling=media_url_handling,
        )

        if conversation is None:
            return None

        # Convert the conversation to include media
        conversation_with_media = _convert_conversation_to_conversation_with_media(
            conversation,
            extract_video_thumbnail,
            extract_videos,
            extract_images,
            extract_card_images,
            video_length_limit,
        )

        # Save to file if requested
        if save_to_file and output_dir is not None:
            tweet_id = json_file.stem
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{tweet_id}_extracted.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(conversation_with_media.model_dump(), f, indent=2)
            logger.info(f"Saved extracted data with media for tweet {tweet_id}")

        return conversation_with_media

    except Exception as e:
        logger.error(f"Error processing {json_file.name} with media: {e}")
        return None


def process_all_tweet_files_with_media(
    tweet_data_dir: Path,
    output_dir: Path,
    media_url_handling: MediaUrlHandling = MediaUrlHandling.KEEP,
    extract_video_thumbnail: bool = False,
    extract_videos: bool = True,
    extract_images: bool = True,
    extract_card_images: bool = True,
    video_length_limit: Optional[int] = None,
) -> None:
    """Process all tweet JSON files in the specified directory and extract conversations with media.

    Args:
        tweet_data_dir: Directory containing tweet JSON files
        output_dir: Directory to save extracted conversations
        media_url_handling: How to handle media URLs in tweet text (keep/replace/remove)
        extract_video_thumbnail: Whether to include thumbnail URLs for videos
        extract_videos: Whether to extract videos and animated GIFs
        extract_images: Whether to extract images
        extract_card_images: Whether to extract images from Twitter cards
        video_length_limit: Optional video length limit in seconds
    """
    # Get all JSON files in the tweet_data directory
    json_files = list(tweet_data_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} tweet files to process")

    processed = 0
    failed = 0
    failed_tweets = []

    for json_file in json_files:
        # Skip if already processed - use EAFP
        tweet_id = json_file.stem
        output_file = output_dir / f"{tweet_id}_extracted.json"

        try:
            # Try to read existing file to check if processing is complete
            with open(output_file, "r") as f:
                json.load(f)  # If this succeeds, file exists and is valid JSON
            logger.info(f"Skipping {tweet_id} - already processed")
            continue
        except (FileNotFoundError, json.JSONDecodeError):
            # File doesn't exist or is corrupted, proceed with processing
            pass

        # Process the file with media
        result = process_single_tweet_file_with_media(
            json_file,
            output_dir,
            save_to_file=True,
            media_url_handling=media_url_handling,
            extract_video_thumbnail=extract_video_thumbnail,
            extract_videos=extract_videos,
            extract_images=extract_images,
            extract_card_images=extract_card_images,
            video_length_limit=video_length_limit,
        )
        if result is not None:
            processed += 1
        else:
            failed += 1
            failed_tweets.append(tweet_id)
            logger.error(f"Failed to process tweet with media: {tweet_id}")

    logger.info(f"Processing complete. Processed: {processed}, Failed: {failed}")
    if failed_tweets:
        logger.info("Failed tweets:")
        for tweet_id in failed_tweets:
            logger.info(f"- {tweet_id}")


def extract_conversation_with_media(
    convo: ThreadedConversationWithInjectionsV2,
    media_url_handling: MediaUrlHandling = MediaUrlHandling.KEEP,
    extract_video_thumbnail: bool = False,
    extract_videos: bool = True,
    extract_images: bool = True,
    extract_card_images: bool = True,
    video_length_limit: Optional[int] = None,
) -> ExtractedConversationWithMedia:
    """Extract conversation with media information directly from a ThreadedConversationWithInjectionsV2.

    This function combines the functionality of extract_conversation and convert_conversation_to_conversation_with_media
    into a single operation for efficiency.

    Args:
        convo: The ThreadedConversationWithInjectionsV2 object containing tweet data
        media_url_handling: How to handle media URLs in tweet text (keep/replace/remove)
        extract_video_thumbnail: Whether to include thumbnail URLs for videos
        extract_videos: Whether to extract videos and animated GIFs
        extract_images: Whether to extract images
        extract_card_images: Whether to extract images from Twitter cards
        video_length_limit: Optional video length limit in seconds

    Returns:
        ExtractedConversationWithMedia containing the main tweet and replies with media information

    Raises:
        ValueError: If no main tweet is found in the conversation data
    """
    # First extract the basic conversation
    conversation = _extract_conversation(convo, media_url_handling)

    # Then convert it to include media information
    return _convert_conversation_to_conversation_with_media(
        conversation,
        extract_video_thumbnail,
        extract_videos,
        extract_images,
        extract_card_images,
        video_length_limit,
    )


if __name__ == "__main__":
    # Example usage for single tweet
    tweet_file = Path("captured_tweet_data.json")

    # Process without saving, keeping original media URLs
    conversation = process_single_tweet_file(
        tweet_file, media_url_handling=MediaUrlHandling.REMOVE
    )
    if conversation:
        print(json.dumps(conversation.model_dump(), indent=2))

    # Example usage for processing all tweets, removing media URLs from text
    # process_all_tweet_files(
    #     settings.tweet_data_dir,
    #     settings.extracted_data_dir,
    #     media_url_handling=MediaUrlHandling.REMOVE
    # )
    process_all_tweet_files_with_media(
        settings.tweet_data_dir,
        settings.extracted_data_dir,
        media_url_handling=MediaUrlHandling.REMOVE,
        video_length_limit=None,
    )
