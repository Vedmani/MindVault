from pydantic import BaseModel, Field, model_validator
from typing import Any, List, Optional, Literal, Union, Dict
from pathlib import Path
import json
from mindvault.core.config import settings

# TweetResult = ForwardRef('TweetResult')
# Tweet = ForwardRef('Tweet')

#TODO Figure out how to use forward references and why this works without them

class QuotedStatusResult(BaseModel):
    result: Optional[Union['_TweetResult', 
                           'TweetWithVisibilityResult', 
                           'TweetTombstone']] = None


# class UserResults(BaseModel):
#     result: Any

#TODO: Handle UserUnavailable, causing bunch of validation errors refer to tweet 1830379345057353995

#TODO: Possibly pending implementation of card for note tweets refer to tweet 1887897486770974770

#TODO: Article tweets are not being scraped refer to tweet 1860767695135973842

class InnerCore(BaseModel):
    created_at: str
    name: str
    screen_name: str

class LegacyInUserResultsInCore(BaseModel):
    can_dm: Optional[bool] = None
    can_media_tag: Optional[bool] = None
    created_at: Optional[str] = None
    default_profile: bool
    default_profile_image: bool
    description: str
    entities: Dict[str, Any]
    fast_followers_count: int
    favourites_count: int
    followers_count: int
    friends_count: int
    has_custom_timelines: bool
    is_translator: bool
    listed_count: int
    location: Optional[str] = None
    media_count: int
    name: Optional[str] = None
    normal_followers_count: int
    pinned_tweet_ids_str: List[str]
    screen_name: Optional[str] = None  # Adding this as it's useful for identification
    

class ResultInsideUserResultsInCore(BaseModel):
    typename: Literal["User"] = Field(alias="__typename")
    id: str
    rest_id: str
    core: InnerCore
    legacy: LegacyInUserResultsInCore

class UserResults(BaseModel):
    result: ResultInsideUserResultsInCore

class Core(BaseModel):
    user_results: UserResults

    def get_user_name(self) -> str:
        return self.user_results.result.core.name or "Unknown Name"

    def get_screen_name(self) -> str:
        return self.user_results.result.core.screen_name or "Unknown User"

class MediaSize(BaseModel):
    h: int
    w: int
    resize: str

class MediaSizes(BaseModel):
    large: MediaSize
    medium: MediaSize
    small: MediaSize
    thumb: MediaSize

class OriginalInfo(BaseModel):
    height: int
    width: int
    focus_rects: List[Any]

class VideoVariant(BaseModel):
    content_type: str
    url: str
    bitrate: Optional[int] = None

class VideoInfo(BaseModel):
    aspect_ratio: List[int]
    duration_millis: Optional[int] = None
    variants: List[VideoVariant]

class AdditionalMediaInfo(BaseModel):
    monetizable: bool

class ExtMediaAvailability(BaseModel):
    status: str

class Media(BaseModel):
    display_url: str
    expanded_url: str
    id_str: str
    indices: List[int]
    media_key: str
    media_url_https: str
    type: Literal["photo", "video", "animated_gif"]
    url: str
    additional_media_info: Optional[AdditionalMediaInfo] = None
    ext_media_availability: ExtMediaAvailability
    sizes: MediaSizes
    original_info: OriginalInfo
    video_info: Optional[VideoInfo] = None

class Url(BaseModel):
    display_url: str
    expanded_url: str
    url: str
    indices: List[int]

class UserMention(BaseModel):
    id_str: str
    name: str
    screen_name: str
    indices: List[int]

class EntitiesInLegacy(BaseModel):
    media: Optional[List[Media]] = None
    user_mentions: List[UserMention]
    urls: List[Url]
    hashtags: List[Any]
    symbols: List[Any]

class EntitySetInNoteTweet(BaseModel):
    user_mentions: List[UserMention]
    urls: List[Url]
    hashtags: List[Any]
    symbols: List[Any]

class QuotedStatusPermalink(BaseModel):
    url: str
    expanded: str
    display: str

class ExtendedEntities(BaseModel):
    media: Optional[List[Media]] = None

class Legacy(BaseModel):
    created_at: str
    conversation_id_str: str
    display_text_range: List[int]
    entities: EntitiesInLegacy
    extended_entities: Optional[ExtendedEntities] = None
    favorite_count: int
    favorited: bool
    full_text: str
    is_quote_status: bool
    lang: str
    quote_count: int
    quoted_status_permalink: Optional[QuotedStatusPermalink] = None
    reply_count: int
    retweet_count: int
    retweeted: bool

class NoteTweetResult(BaseModel):
    id: str
    text: str
    entity_set: EntitySetInNoteTweet
    # richtext: Dict[str, Any] #This might need to be optional

class NoteTweetResults(BaseModel):
    result: NoteTweetResult

class NoteTweet(BaseModel):
    note_tweet_results: NoteTweetResults

class ImageValue(BaseModel):
    alt: str
    height: int
    width: int
    url: str

class ImageColorRGB(BaseModel):
    blue: int
    green: int
    red: int

class ImageColorPalette(BaseModel):
    rgb: ImageColorRGB
    percentage: float

class ImageColorValue(BaseModel):
    palette: List[ImageColorPalette]

class BindingValue(BaseModel):
    key: str
    value: Dict[str, Any]  # This could be further typed but varies significantly

class CardPlatformPlatform(BaseModel):
    audience: Dict[str, str]
    device: Dict[str, str]

class CardPlatform(BaseModel):
    platform: CardPlatformPlatform

class UserRefResult(BaseModel):
    typename: Literal["User", "UserUnavailable"] = Field(alias="__typename")
    id: Optional[str] = None
    rest_id: Optional[str] = None
    affiliates_highlighted_label: Optional[Dict[str, Any]] = None
    has_graduated_access: Optional[bool] = None
    is_blue_verified: Optional[bool] = None
    legacy: Optional[LegacyInUserResultsInCore] = None
    smart_blocked_by: Optional[bool] = None
    smart_blocking: Optional[bool] = None
    business_account: Optional[Dict[str, Any]] = None

    @model_validator(mode='after')
    def validate_fields_based_on_typename(self):
        if self.typename == "User":
            required_fields = [
                'id', 'rest_id', 'affiliates_highlighted_label',
                'has_graduated_access', 'is_blue_verified', 'legacy',
                # 'smart_blocked_by', 'smart_blocking', 'business_account'
            ]
            for field in required_fields:
                if getattr(self, field) is None:
                    raise ValueError(f"{field} is required when typename is 'User'")
        return self

class UserRefResults(BaseModel):
    result: UserRefResult

class CardLegacy(BaseModel):
    binding_values: List[BindingValue]
    card_platform: CardPlatform
    name: str
    url: str
    user_refs_results: List[UserRefResults]

class Card(BaseModel):
    rest_id: str
    legacy: Optional[CardLegacy] = None


# --- Article Schema Models ---

class ArticleMediaInfo(BaseModel):
    """Media info for an article media entity."""
    typename: Optional[str] = Field(alias="__typename", default=None)
    original_img_height: Optional[int] = None
    original_img_width: Optional[int] = None
    original_img_url: Optional[str] = None
    color_info: Optional[Dict[str, Any]] = None


class ArticleMediaEntity(BaseModel):
    """A media entity in an article (image, video, etc.)."""
    id: str
    media_key: str
    media_id: str
    media_info: ArticleMediaInfo


class ArticleContentBlock(BaseModel):
    """A block in the article content_state (DraftJS format)."""
    key: str
    data: Dict[str, Any] = {}
    entityRanges: List[Dict[str, Any]] = []
    inlineStyleRanges: List[Dict[str, Any]] = []
    text: str
    type: str  # "unstyled", "atomic", "header-one", "header-two", "ordered-list-item", etc.


class ArticleEntityMapItem(BaseModel):
    """An item in the entityMap list."""
    key: str
    value: Dict[str, Any]


class ArticleContentState(BaseModel):
    """The content_state of an article (DraftJS format)."""
    blocks: List[ArticleContentBlock]
    entityMap: List[ArticleEntityMapItem] = []


class ArticleCoverMedia(BaseModel):
    """Cover media for an article."""
    id: str
    media_key: str
    media_id: str
    media_info: ArticleMediaInfo  # Reuse ArticleMediaInfo instead of duplicate



class ArticleResultData(BaseModel):
    """The result data for an article."""
    rest_id: str
    id: str
    title: str
    preview_text: Optional[str] = None
    cover_media: Optional[ArticleCoverMedia] = None
    content_state: Optional[ArticleContentState] = None
    media_entities: List[ArticleMediaEntity] = []
    lifecycle_state: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ArticleResults(BaseModel):
    """Wrapper for article results."""
    result: ArticleResultData


class Article(BaseModel):
    """An article attached to a tweet."""
    article_results: ArticleResults


# --- End Article Schema Models ---


class _TweetResult(BaseModel):
    typename: Literal["Tweet"] = Field(alias="__typename")
    rest_id: str
    has_birdwatch_notes: bool
    core: Core
    unmention_data: Dict[str, Any]
    edit_control: Dict[str, Any]
    is_translatable: bool
    quoted_status_result: Optional[QuotedStatusResult] = None
    views: Dict[str, Any]
    source: str
    legacy: Legacy
    note_tweet: Optional[NoteTweet] = None
    card: Optional[Card] = None
    article: Optional[Article] = None



class Tweet(BaseModel):
    rest_id: str
    has_birdwatch_notes: bool
    core: Core
    unmention_data: Dict[str, Any]
    edit_control: Dict[str, Any]
    is_translatable: bool
    quoted_status_result: Optional[QuotedStatusResult] = None
    views: Dict[str, Any]
    source: str
    legacy: Legacy
    note_tweet: Optional[NoteTweet] = None
    card: Optional[Card] = None
    article: Optional[Article] = None


class TweetWithVisibilityResult(BaseModel):
    typename: Optional[Literal["TweetWithVisibilityResults", "UserUnavailable", "Tweet"]] = Field(alias="__typename", default=None)
    tweet: Optional[Tweet] = None

    @model_validator(mode='after')
    def validate_fields_based_on_typename(self):
        if self.typename == "TweetWithVisibilityResults":
            if self.tweet is None:
                raise ValueError("tweet is required when typename is 'TweetWithVisibilityResults'")
        return self


class TweetTombstone(BaseModel):
    typename: Literal["TweetTombstone", "Tweet"] = Field(alias="__typename")
    tombstone: Optional[Any] = None


class TweetResult(BaseModel):
    result: Union[_TweetResult, TweetWithVisibilityResult, TweetTombstone]
    is_note_tweet: bool = Field(default=False)

    # This might slow down the code alot
    @model_validator(mode="after")
    def set_note_tweet_flag(self):
        # Check if result is _TweetResult or inside TweetWithVisibilityResult
        tweet_result = (
            self.result if isinstance(self.result, _TweetResult) 
            else self.result.tweet if isinstance(self.result, TweetWithVisibilityResult)
            else None
        )
        
        self.is_note_tweet = (
            tweet_result is not None 
            and tweet_result.note_tweet is not None
        )
        return self


class ItemContent(BaseModel):
    itemType: Literal[
        "TimelineTweet", "TimelineTimelineModule", "TimelineTimelineCursor"
    ]
    typename: Optional[
        Literal["TimelineTweet", "TimelineTimelineModule", "TimelineTimelineCursor"]
    ] = Field(alias="__typename")
    tweet_results: Optional[TweetResult] = None
    tweetDisplayType: Optional[Literal["Tweet", "SelfThread"]] = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.itemType != "TimelineTimelineCursor":
            if self.tweet_results is None:
                raise ValueError(
                    "tweet_results is required when itemType is not 'TimelineTimelineCursor'"
                )
            if self.tweetDisplayType is None:
                raise ValueError(
                    "tweetDisplayType is required when itemType is not 'TimelineTimelineCursor'"
                )
        return self

class ItemDictFromItemsList(BaseModel):
    itemContent: ItemContent
    clientEventInfo: Dict[str, Any]

    
class ItemFromItemsList(BaseModel):
    entryId: str
    item: ItemDictFromItemsList


class Content(BaseModel):
    entryType: Literal["TimelineTimelineItem", "TimelineTimelineModule", "TimelineTimelineCursor"]
    typename: Literal["TimelineTimelineItem", "TimelineTimelineModule", "TimelineTimelineCursor"] = Field(
        alias="__typename"
    )
    itemContent: Optional[ItemContent] = None
    items: Optional[List[ItemFromItemsList]] = None
# TODO: Add aftervalidator possibly based on conversation thread and main tweet


class Entry(BaseModel):
    entryId: str
    sortIndex: str
    content: Content
    entry_type: Literal["main_tweet", "conversation"] = Field(default="conversation")

    @model_validator(mode="after")
    def validate_content_fields(self):
        # Set entry_type based on entryId
        if self.entryId.startswith("tweet-"):
            self.entry_type = "main_tweet"
            if self.content.itemContent is None:
                raise ValueError(
                    "itemContent is required when entryId starts with 'tweet-'"
                )
        if (
            self.entryId.startswith("conversationthread-")
            and self.content.items is None
        ):
            raise ValueError(
                "items is required when entryId starts with 'conversationthread-'"
            )
        return self


class Instruction(BaseModel):
    # Allow both instruction types
    type: Literal["TimelineAddEntries", "TimelineTerminateTimeline", "TimelineClearCache"]
    entries: Optional[List[Entry]] = None

    @model_validator(mode="after")
    def check_entries(self):
        if self.type == "TimelineAddEntries" and self.entries is None:
            raise ValueError("entries cannot be None when type is 'TimelineAddEntries'")
        return self


class ThreadedConversationWithInjectionsV2(BaseModel):
    # Both JSON files include instructions.
    instructions: List[Instruction]
    # One model includes metadata and the other does not; mark it optional.
    # metadata: Optional[Any] = None #TODO: remove optional


class TweetData(BaseModel):
    threaded_conversation_with_injections_v2: ThreadedConversationWithInjectionsV2

    def __str__(self):
        #TODO: This is not perfect yet, check for edge cases
        # Helper function to extract tweet text from an ItemContent.
        def extract_tweet_text(item_content: ItemContent) -> tuple[str, str, Optional[tuple[str, str, str]]]:
            if item_content.tweet_results is None:
                return "[No tweet text available]", "", None
            tweet_result = item_content.tweet_results
            result = tweet_result.result
            # If the tweet is marked as a tombstone (unavailable), return a placeholder.
            if isinstance(result, TweetTombstone):
                return "[Tweet unavailable]", "", None
            
            # Get the actual tweet object, handling different result types
            tweet = (result.tweet if hasattr(result, "tweet") 
                    else result if hasattr(result, "legacy") 
                    else None)
            
            if tweet is None:
                return "[Unknown tweet format]", "", None
                
            # Get the user name
            user_name = tweet.core.get_screen_name() if hasattr(tweet, "core") else "Unknown User"
            
            # Extract quoted tweet if present
            quoted_content = None
            if tweet.quoted_status_result and tweet.quoted_status_result.result:
                quoted_tweet = tweet.quoted_status_result.result
                if hasattr(quoted_tweet, "tweet"):
                    quoted_tweet = quoted_tweet.tweet
                if hasattr(quoted_tweet, "legacy"):
                    quoted_user = quoted_tweet.core.get_screen_name() if hasattr(quoted_tweet, "core") else "Unknown User"
                    quoted_text = quoted_tweet.legacy.full_text
                    quoted_link = tweet.legacy.quoted_status_permalink.expanded if hasattr(tweet.legacy, "quoted_status_permalink") else ""
                    quoted_content = (quoted_text.strip(), quoted_user, quoted_link)
            
            # If a note tweet is provided, use its complete text
            if tweet.note_tweet is not None:
                return tweet.note_tweet.note_tweet_results.result.text, user_name, quoted_content
            
            # Clean up the text by removing trailing URLs if they're at the end of the text
            text = tweet.legacy.full_text
            if tweet.legacy.entities and tweet.legacy.entities.urls:
                for url in tweet.legacy.entities.urls:
                    if text.endswith(url.url):
                        text = text[:-len(url.url)].strip()
            
            return text.strip(), user_name, quoted_content

        main_tweet_text = None
        main_tweet_user = None
        main_tweet_quote = None
        replies = []

        # Iterate over all instructions in the conversation.
        for instruction in self.threaded_conversation_with_injections_v2.instructions:
            if instruction.type != "TimelineAddEntries" or not instruction.entries:
                continue
                
            for entry in instruction.entries:
                # Skip related tweets
                if entry.entryId.startswith("tweetdetailrelatedtweets"): # These are related tweets which are recommended by twitter and are not part of the conversation.
                    continue
                    
                # Process main tweet entry.
                if (entry.entry_type == "main_tweet" and 
                    entry.content and entry.content.itemContent):
                    main_tweet_text, main_tweet_user, main_tweet_quote = extract_tweet_text(entry.content.itemContent)
                
                # Process conversation replies.
                elif entry.entry_type == "conversation":
                    if entry.content.items:
                        for item in entry.content.items:
                            if (item and item.item and 
                                item.item.itemContent and 
                                item.item.itemContent.tweet_results):
                                text, user, quote = extract_tweet_text(item.item.itemContent)
                                replies.append((text, user, quote))
                    elif entry.content.itemContent:
                        text, user, quote = extract_tweet_text(entry.content.itemContent)
                        replies.append((text, user, quote))

        # Build the formatted output.
        parts = []
        if main_tweet_text and main_tweet_user:
            parts.append(f"Main Tweet by {main_tweet_user}:")
            parts.append(main_tweet_text)
            if main_tweet_quote:
                quoted_text, quoted_user, quoted_link = main_tweet_quote
                parts.append(f"\nQuoting @{quoted_user}:")
                parts.append(f"  {quoted_text}")
                if quoted_link:
                    parts.append(f"  Link to quoted tweet: {quoted_link}")

        if replies:
            parts.append("\nReplies:")
            for text, user, quote in replies:
                parts.append(f"- {user}: {text}")
                if quote:
                    quoted_text, quoted_user, quoted_link = quote
                    parts.append(f"  Quoting @{quoted_user}:")
                    parts.append(f"    {quoted_text}")
                    if quoted_link:
                        parts.append(f"    Link to quoted tweet: {quoted_link}")
        
        return "\n".join(parts) if parts else "[No content available]"

    # def __repr__(self):
    #     return self.__str__()

def validate_tweet_data_directory(tweet_data_dir: Path) -> None:
    """
    Validates all JSON files in the given directory against the TweetData schema.

    Args:
        tweet_data_dir: The path to the directory containing tweet data JSON files.
    """
    for file_path in tweet_data_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            TweetData.model_validate(data)
            print(f"Validation successful for {file_path}")
        except Exception:
            raise


if __name__ == "__main__":
    validate_tweet_data_directory(settings.tweet_data_dir)