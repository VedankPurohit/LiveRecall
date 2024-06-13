import json
import os
import numpy as np




def LoadJson(file_path):
    ImageNames = []
    ListOfVectors = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
            
            for item in data:
                ImageNames.append(item["FileName"])
                ListOfVectors.append(np.array(item["ImgEmbeding"], dtype=np.float32))
                
        print(f"Data loaded from '{file_path}'.")
    else:
        print(f"File '{file_path}' does not exist.")
    return ImageNames, ListOfVectors

def SaveJson(file_path,ImageNames,ListOfVectors):
    data_to_save = [{"FileName": name, "ImgEmbeding": embedding.tolist()} for name, embedding in zip(ImageNames, ListOfVectors)]
    
    with open(file_path, 'w') as file:
        json.dump(data_to_save, file, indent=4)
        
    print(f"Data saved to '{file_path}'.")



