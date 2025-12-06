import os
import time
import ClipMode as ClipMode
from DB_Connection import db
import re
from datetime import datetime

def extract_timestamp_from_filename(filename):
    """
    Extract timestamp from filename (format: Snap-YYMMDDHHMMSS)
    If no timestamp found, return None
    """
    pattern = r'Snap-(\d{12})'
    match = re.search(pattern, filename)
    
    if match:
        return match.group(1)
    return None

def get_oldest_timestamp(image_dir):
    """
    Get the oldest timestamp from files with valid timestamps
    If no valid timestamps found, return current time
    """
    oldest_time = None

    count = 0
    
    for filename in os.listdir(image_dir):
        count += 1
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue
            
        timestamp = extract_timestamp_from_filename(filename)
        if timestamp:
            if oldest_time is None or timestamp < oldest_time:
                oldest_time = timestamp
    print(count)
    if oldest_time is None:
        # Return current time in YYMMDDhhmmss format
        return time.strftime("%y%m%d%H%M%S")
    return str(int(oldest_time) - 100000)

def migrate_images_to_db(image_dir="CapturedData", rebuild=False):
    """
    Migrate images from a directory to the database.
    If rebuild is True, it deletes everything in the database and then adds all images.
    If rebuild is False (default), it only adds images that are not already in the database.

    Args:
        image_dir (str): Directory containing image files.
        rebuild (bool): Whether to rebuild the database.
    
    Returns:
        int: Number of images successfully migrated.
    """
    print(f"Starting migration from '{image_dir}' to the database.")
    
    db.connect()
    db.initialize_memory_tables()
    print("Database initialized successfully.")

    if rebuild:
        print("Rebuild mode enabled: Deleting all existing image records from the database.")
        try:
            db.execute("DELETE FROM LiveRecall")
            print("Database cleared successfully.")
        except Exception as e:
            print(f"Error clearing the database: {e}")
            db.disconnect()
            return 0
    print("Fetching oldest timestamp...")
    oldest_timestamp = get_oldest_timestamp(image_dir)
    print(f"Oldest timestamp for fallback: {oldest_timestamp}")

    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    total_files = len(image_files)
    print(f"Found {total_files} images to process.")

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    for i, filename in enumerate(image_files):
        image_path = os.path.join(image_dir, filename)
        
        try:
            if not rebuild:
                # This assumes a 'fetchone' method exists in the DB_Connection module.
                exists_query = "SELECT 1 FROM LiveRecall WHERE image_path = %s"
                result = db.cur.fetchone(exists_query, (image_path,))
                if result:
                    skipped_count += 1
                    continue

            timestamp = extract_timestamp_from_filename(filename) or oldest_timestamp
            
            embedding = ClipMode.ImgEmb(image_path)
            embedding_list = embedding.tolist()
            
            insert_query = """
                INSERT INTO LiveRecall (image_path, embedding, timestamp)
                VALUES (%s, %s, %s)
            """
            db.execute(insert_query, (image_path, embedding_list, timestamp))
            migrated_count += 1
            
            if (migrated_count) % 10 == 0 and migrated_count > 0:
                print(f"Migrated {migrated_count} new images...")

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            error_count += 1

    print("\nMigration complete.")
    print(f"Successfully migrated: {migrated_count}")
    print(f"Skipped (already exist): {skipped_count}")
    print(f"Errors: {error_count}")
    
    db.disconnect()
    return migrated_count



print("Debug: Script started")

if __name__ == "__main__":
    # Start timing the migration
    start_time = time.time()
    print("Hi")
    
    # Run the migration
    print(f"Oldest timestamp: {get_oldest_timestamp(image_dir='CapturedData')}")
    processed_count = migrate_images_to_db()
    
    # Calculate and display elapsed time
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    
    print(f"Total migration time: {minutes} minutes, {seconds} seconds")
    print(f"Successfully migrated {processed_count} images to the database")