import json
import os
import numpy as np
import time

def TimeField():
    return time.strftime("%y%m%d%H%M%S")




def LoadJson(file_path):
    ImageNames = []
    ListOfVectors = []
    TimeLine = []
    CurrentTime = TimeField()
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
            
            for item in data:
                ImageNames.append(item["FileName"])
                ListOfVectors.append(np.array(item["ImgEmbeding"], dtype=np.float32))
                TimeLine.append(item.get("TimeLine", CurrentTime)) # Old virsion Didn't have TimeLine
            if "TimeLine" not in item:
                SaveJson(file_path,ImageNames,ListOfVectors, TimeLine)
                print("Added Timeline")
                
        print(f"Data loaded from '{file_path}'.")
        
    else:
        print(f"File '{file_path}' does not exist.")
    return ImageNames, ListOfVectors, TimeLine

def SaveJson(file_path,ImageNames,ListOfVectors, TimeLine):
    data_to_save = [{"FileName": name, "ImgEmbeding": embedding.tolist(), "TimeLine": Time} for name, embedding, Time in zip(ImageNames, ListOfVectors,TimeLine)]
    
    with open(file_path, 'w') as file:
        json.dump(data_to_save, file, indent=4)
        
    print(f"Data saved to '{file_path}'.")



