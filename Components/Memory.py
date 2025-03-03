import Components.ClipMode as ClipMode
import time
import torch
import numpy as np
from Components.DB_Connection import db

def TimeField():
    return time.strftime("%y%m%d%H%M%S")

# Initialize database connection when module is imported
db.connect()
db.initialize_memory_tables()

def AddToMemory(image_path):
    """
    Add an image to memory by storing its embedding in the database
    
    Args:
        image_path: Path to the image file
        
    Returns:
        bool: Success status
    """
    try:
        # Generate embedding
        embedding = ClipMode.ImgEmb(image_path)
        
        # Convert embedding to list for database storage
        embedding_list = embedding.tolist() # [0] ?
        
        # Get current timestamp
        timestamp = TimeField()
        
        # Store in database
        query = """
            INSERT INTO LiveRecall (image_path, embedding, timestamp)
            VALUES (%s, %s, %s)
        """
        db.execute(query, (image_path, embedding_list, timestamp))
        return True
    except Exception as e:
        print(f"Error adding to memory: {e}")
        return False

def AutoAddMemory(CaptureImage, cap, Timer, MaxBufferSize):
    """
    Automatically add images to memory at regular intervals
    
    Args:
        CaptureImage: Image capture function
        cap: Capture device
        Timer: Time between captures
        MaxBufferSize: Maximum number of images to keep
    """
    buffer_count = 0
    
    while True:
        if buffer_count > MaxBufferSize:
            buffer_count = 0
            # Delete oldest records to maintain buffer size
            query = """
                DELETE FROM LiveRecall
                WHERE id IN (
                    SELECT id FROM LiveRecall
                    ORDER BY id ASC
                    LIMIT %s
                )
            """
            db.execute(query, (MaxBufferSize // 2,))
            
        time.sleep(Timer)
        location = f"Vision AI/Temp/Image{buffer_count}.png"
        CaptureImage.ClearestImg(1, 200, cap=cap, image=location)
        AddToMemory(location)
        buffer_count += 1

def GetMemory(limit=None): ##Lagacy Option
    """
    Retrieve all memory snapshots from the database
    
    Args:
        limit: Optional limit on number of records to retrieve
        
    Returns:
        tuple: (embeddings_list, image_paths_list, timestamps_list)
    """
    try:
        if limit:
            query = """
                SELECT embedding, image_path, timestamp FROM LiveRecall
                ORDER BY id DESC LIMIT %s
            """
            db.execute(query, (limit,))
        else:
            query = """
                SELECT embedding, image_path, timestamp FROM LiveRecall
                ORDER BY id DESC
            """
            db.execute(query)
            
        results = db.fetch_all()
        
        memory_snapshots = []
        image_names = []
        timeline = []
        
        for row in results:
            memory_snapshots.append(torch.tensor(row[0]))
            image_names.append(row[1])
            timeline.append(row[2])
            
        return memory_snapshots, image_names, timeline
    except Exception as e:
        print(f"Error getting memory: {e}")
        return [], [], []

def ClearMemory():
    """
    Clear all memory snapshots from the database
    
    Returns:
        bool: Success status
    """
    try:
        query = "TRUNCATE TABLE LiveRecall"
        success = db.execute(query)
        return success
    except Exception as e:
        print(f"Error clearing memory: {e}")
        return False

def RetriveMemory(embedding):
    """
    Retrieve the most similar image to the given embedding
    
    Args:
        embedding: Vector embedding to compare against
        
    Returns:
        tuple: (image_path, similarity_score)
    """
    try:
        # Convert embedding to list
        embedding_list = "["+ ",".join(str(x) for x in embedding.tolist()) +"]"
        
        # Use pgvector to find the most similar embedding
        # query = """
        #     SELECT image_path, 1 - (embedding <=> %s) AS similarity
        #     FROM LiveRecall
        #     ORDER BY embedding <=> %s
        #     LIMIT 1
        # """
        # db.execute(query, (embedding_list, embedding_list))
        query = """
            SELECT image_path, embedding
            FROM LiveRecall
            ORDER BY embedding <=> %s
            LIMIT 1
        """
        db.execute(query, (embedding_list,))
        
        result = db.fetch_one()
        if result:
            return result[0], ClipMode.CosSemilarity(embedding, result[1])
        else:
            return None, 0
    except Exception as e:
        print(f"Error retrieving memory: {e}")
        return None, 0

def RetriveMemoryMax(embedding, number= 6): #Half from one Cos and other from Dot
    """
    Retrieve the top N most similar images to the given embedding
    
    Args:
        embedding: Vector embedding to compare against
        number: Number of results to return
        
    Returns:
        tuple: (list_of_image_paths, similarity_scores)
    """
    try:
        print("Starting retrival")
        # Convert embedding to list
        embedding_list = "["+ ",".join(str(x) for x in embedding.tolist()) +"]"
        
        # Use pgvector to find the most similar embeddings
        query = """
            SELECT image_path, (embedding <=> %s) AS similarity
            FROM LiveRecall
            ORDER BY embedding <=> %s
            LIMIT %s
        """
        db.execute(query, (embedding_list, embedding_list, number))
        
        results = db.fetch_all()
        
        image_paths = []
        similarities = []
        
        for row in results:
            image_paths.append(row[0])
            similarities.append(row[1])
            
        print(f"Retrieved from Cos images count: {len(image_paths)}")
    
        print("Cosin Similarity returned this - ")
        for i in range(len(image_paths)):
            print(f"{i} - Image path = {image_paths[i]}, Similarity = {similarities[i]} \n")

        

        if True:    #if len(image_paths) == 0: 
            print("Cosine similarity returned no results, trying dot product")
            query = """
                SELECT image_path, embedding <#> %s AS similarity
                FROM LiveRecall
                ORDER BY embedding <#> %s
                LIMIT %s
            """
            db.execute(query, (embedding_list, embedding_list, number))
            
            results = db.fetch_all()
            
            image_paths2 = []
            similarities2 = []
            
            for row in results:
                image_paths2.append(row[0])
                similarities2.append(row[1])
                
            print(f"Retrieved from Dot images count: {len(image_paths)}")

            print("Dot Similarity returned this - ")
            for i in range(len(image_paths2)):
                print(f"{i} - Image path = {image_paths2[i]}, Similarity = {similarities2[i]} \n")
        
        for i in range(len(image_paths2)):
            if image_paths2[i] not in image_paths:
                image_paths.append(image_paths2[i])
                similarities.append(similarities2[i])
                
            
        return image_paths, similarities
    except Exception as e:
        print(f"Error retrieving memory: {e}")
        return [], []

# Add a function to close the database connection when the application exits
def cleanup():
    """Close database connection"""
    db.disconnect()

# For command-line testing
if __name__ == "__main__":
    print("Testing database memory system")
    
    # Initialize tables
    db.initialize_memory_tables()
    
    # Print the number of records
    db.execute("SELECT COUNT(*) FROM LiveRecall")
    count = db.fetch_one()[0]
    print(f"Current memory count: {count}")
    
    # Interactive testing
    while True:
        text = input("Enter Text (or 'exit' to quit): ")
        if text.lower() == 'exit':
            break
            
        emb = ClipMode.TextEmb(text)
        result, similarity = RetriveMemoryMax(emb, 10)
        print(f"Most similar image: {result}")
        print(f"Similarity score: {similarity}")
        
    # Clean up
    cleanup()












# import Components.ClipMode as ClipMode
# import torch
# import time
# import Components.JsonData as JsonData
# def TimeField():
#     return time.strftime("%y%m%d%H%M%S")


# ImageNames, MemorySnapShot, TimeLine = JsonData.LoadJson("Data.json")

# print(len(MemorySnapShot), len(ImageNames), len(TimeLine))



# def AddToMemory(Image):
#     Embedding = ClipMode.ImgEmb(Image)
#     MemorySnapShot.append(Embedding)
#     ImageNames.append(Image)
#     TimeLine.append(TimeField())
#     return True

# def AutoAddMemory(CaptureImage, cap, Timer, MaxBufferSize):
#     BufferSize = 0
#     while True:
#         if BufferSize > MaxBufferSize:
#             BufferSize = 0
#             MemorySnapShot = MemorySnapShot[:MaxBufferSize]
#             ImageNames = ImageNames[:MaxBufferSize]
#         time.sleep(Timer)
#         Location = f"Vision AI\Temp\Image{BufferSize}.png"
#         CaptureImage.ClearestImg(1,200,cap=cap, image=Location)
#         AddToMemory(Location)




# def GetMemory():
#     return MemorySnapShot, ImageNames, TimeLine

# def ClearMemory():
#     MemorySnapShot = []
#     ImageNames = []
#     TimeLine = []
#     return True

# def RetriveMemory(Embedding):
#     Semilarity = ClipMode.DotSemilarity(Embedding, MemorySnapShot)
#     Index = torch.argmax(Semilarity)
#     return ImageNames[Index], Semilarity


# def RetriveMemoryMax(Embedding, Number):
#     Semilarity = ClipMode.DotSemilarity(Embedding, MemorySnapShot)
#     values, Indexs = torch.topk(Semilarity, Number)
#     print(Indexs)
#     Lis = []
#     for Index in Indexs[0]:
#         if isinstance(Index.item(), int):
#             print(Index.item())
#             Lis.append(ImageNames[Index.item()])

#     if len(Lis) == 0:
#         print("List returned 0?")
#         Semilarity = ClipMode.CosSemilarity(Embedding, MemorySnapShot)
#         values, Indexs = torch.topk(Semilarity, Number)
#         print(Indexs)
#         Lis = []
#         for Index in Indexs[0]:
#             if isinstance(Index.item(), int):
#                 print(Index.item())
#                 Lis.append(ImageNames[Index.item()])

#     print("Retrived images count : ", + len(Lis))
#     print(Lis)

#     return Lis, Semilarity



# if __name__ == "__main__":


#     print(len(GetMemory()[0]))
#     while True:
#         Text = input("Enter Text: ")
#         Emb = ClipMode.TextEmb(Text)
#         print(RetriveMemory(Emb))