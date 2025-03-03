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

def migrate_images_to_db(image_dir="CapturedData"):
    """
    Migrate all images from a directory to the database
    
    Args:
        image_dir: Directory containing image files
        
    Returns:
        int: Number of images processed
    """
    print(f"Starting migration from {image_dir} directory to database...")
    
    # Initialize database
    db.connect()
    db.initialize_memory_tables()
    
    # Get the oldest timestamp to use as fallback
    oldest_timestamp = get_oldest_timestamp(image_dir)
    print(f"Oldest timestamp found: {oldest_timestamp}")
    
    # Process all images
    count = 0
    error_count = 0
    
    # Get list of image files
    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    total_files = len(image_files)
    print(f"Found {total_files} image files to process")
    
    for filename in image_files:
        try:
            # Full path to image
            image_path = os.path.join(image_dir, filename)
            
            # Extract timestamp or use oldest as fallback
            timestamp = extract_timestamp_from_filename(filename) or oldest_timestamp
            
            # Compute embedding
            print(f"Processing {filename}...")
            embedding = ClipMode.ImgEmb(image_path)
            embedding_list = embedding.tolist()
            
            # Insert into database
            query = """
                INSERT INTO LiveRecall (image_path, embedding, timestamp)
                VALUES (%s, %s, %s)
            """
            db.execute(query, (image_path, embedding_list, timestamp))
            count += 1
            
            if count % 10 == 0:
                print(f"Processed {count}/{total_files} images")
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            error_count += 1
    
    print(f"Migration complete. Processed {count} images with {error_count} errors.")
    db.disconnect()
    return count


print("Debug: Script started")

if __name__ == "__main__":
    # Start timing the migration
    start_time = time.time()
    print("Hi")
    
    # Run the migration
    print(get_oldest_timestamp(image_dir="CapturedData"))
    processed_count = migrate_images_to_db()
    
    # Calculate and display elapsed time
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    
    print(f"Total migration time: {minutes} minutes, {seconds} seconds")
    print(f"Successfully migrated {processed_count} images to the database")