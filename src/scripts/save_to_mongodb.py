#!/usr/bin/env python3

import os
import json
import glob
import re
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

# MongoDB connection information
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "mindvault"
RAW_DATA_COLLECTION = "raw-data"
EXTRACTED_DATA_COLLECTION = "extracted-data"

# Directories containing JSON files
RAW_DATA_DIR = "/Users/vedmani/projects/MindVault/artifacts/tweet_data"
EXTRACTED_DATA_DIR = "/Users/vedmani/projects/MindVault/artifacts/extracted_data"

def connect_to_mongodb():
    """Connect to MongoDB and return the database instance"""
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

def extract_tweet_id_from_filename(file_path):
    """Extract tweet_id from filename
    
    Format for raw files: {tweet_id}.json
    Format for extracted files: {tweet_id}_extracted.json
    """
    base_name = os.path.basename(file_path)
    # Remove .json extension
    base_name = base_name.replace('.json', '')
    # Remove _extracted suffix if present
    base_name = base_name.replace('_extracted', '')
    return base_name

def save_files_to_collection(directory, collection: Collection):
    """Save all JSON files from the directory to the specified collection"""
    json_files = glob.glob(os.path.join(directory, "*.json"))
    
    if not json_files:
        print(f"No JSON files found in {directory}")
        return 0
    
    count = 0
    for file_path in json_files:
        try:
            # Extract tweet_id from filename
            tweet_id = extract_tweet_id_from_filename(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # If data is a list, insert each item separately with the tweet_id
            if isinstance(data, list):
                if data:
                    # Add _id to each document in the list
                    for item in data:
                        item['_id'] = tweet_id
                    
                    try:
                        result = collection.insert_many(data, ordered=False)
                        count += len(result.inserted_ids)
                    except DuplicateKeyError as e:
                        # Some documents may have been inserted before the error
                        print(f"Some documents already exist in the collection: {str(e)}")
            else:
                # Set _id to tweet_id for single document
                data['_id'] = tweet_id
                
                try:
                    result = collection.insert_one(data)
                    count += 1
                except DuplicateKeyError:
                    print(f"Document with tweet_id {tweet_id} already exists, updating instead")
                    # Update the document if it already exists
                    result = collection.replace_one({'_id': tweet_id}, data, upsert=True)
                
            print(f"Processed {file_path}")
        except json.JSONDecodeError:
            print(f"Error: {file_path} is not a valid JSON file")
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
    
    return count

def main():
    # Connect to MongoDB
    db = connect_to_mongodb()
    
    # Save raw data
    raw_data_collection = db[RAW_DATA_COLLECTION]
    print(f"\nSaving files from {RAW_DATA_DIR} to '{RAW_DATA_COLLECTION}' collection...")
    raw_count = save_files_to_collection(RAW_DATA_DIR, raw_data_collection)
    print(f"Added {raw_count} documents to '{RAW_DATA_COLLECTION}' collection")
    
    # Save extracted data
    extracted_data_collection = db[EXTRACTED_DATA_COLLECTION]
    print(f"\nSaving files from {EXTRACTED_DATA_DIR} to '{EXTRACTED_DATA_COLLECTION}' collection...")
    extracted_count = save_files_to_collection(EXTRACTED_DATA_DIR, extracted_data_collection)
    print(f"Added {extracted_count} documents to '{EXTRACTED_DATA_COLLECTION}' collection")
    
    print("\nProcess completed!")

if __name__ == "__main__":
    main()
