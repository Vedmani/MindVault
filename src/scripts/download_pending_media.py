import asyncio
from pathlib import Path
from mindvault.bookmarks.twitter.extract import (
    extract_media_info_from_conversation,
    ExtractedMediaList
)
from mindvault.bookmarks.twitter.download_tweet_media import download_tweet_media, get_file_path
from mindvault.core.config import settings
from mindvault.bookmarks.twitter.extract import ExtractedConversation
import json
import time

def get_media_list():
    media_list = []
    for file in Path(settings.extracted_data_dir).glob("*.json"):
        with open(file, "r") as f:
            data = json.load(f)
            conversation = ExtractedConversation(**data)
            _media_list = extract_media_info_from_conversation(
                conversation, extract_card_images=False, video_length_limit=None
            )
            media_list.extend(_media_list.media)
    print(f"Found {len(media_list)} media to download")
    
    # Filter out media items that have already been downloaded by checking the actual files
    filtered_media_list = []
    already_downloaded_count = 0
    zero_byte_files_count = 0
    
    for media in media_list:
        file_path = get_file_path(media, settings.media_dir)
        if not file_path.exists():
            filtered_media_list.append(media)
        elif file_path.stat().st_size == 0:
            # Include zero-byte files for redownloading
            filtered_media_list.append(media)
            zero_byte_files_count += 1
        else:
            already_downloaded_count += 1
    
    print("Already downloaded media:", already_downloaded_count)
    print("Zero-byte files to retry:", zero_byte_files_count)
    print("Remaining media to download:", len(filtered_media_list))
    
    return filtered_media_list


async def main():
    media_list = get_media_list()
    batch_size = 50
    total_media = len(media_list)
    
    for i in range(0, total_media, batch_size):
        batch = media_list[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(total_media + batch_size - 1)//batch_size} ({len(batch)} items)")
        results = await download_tweet_media(
            output_dir=settings.media_dir,
            media_list=ExtractedMediaList(media=batch),
            max_connections=50
        )
        print(f"Completed batch {i//batch_size + 1}")

if __name__ == "__main__":
    asyncio.run(main())