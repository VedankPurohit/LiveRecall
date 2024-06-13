import os
from Memory import AddToMemory, ClipMode, RetriveMemoryMax, GetMemory, JsonData
from PIL import Image
import time

def display_image(image_path):
    img = Image.open(image_path)
    print("Opening image...", image_path)
    img.show()

def process_png_files(folder_path):
    if not os.path.exists(folder_path):
        print(f"The folder {folder_path} does not exist.")
        return
    count = 0

    for file_name in os.listdir(folder_path):
        if file_name.lower().endswith('.png'):
            file_path = os.path.join(folder_path, file_name)
            print(file_path)
            count+= 1
            AddToMemory(file_path)
    print(count)



process_png_files(r'CapturedData')

while __name__ == "__main__":
    Text = input("Enter Text: ")
    Emb = ClipMode.TextEmb(Text)
    Ans, _ = RetriveMemoryMax(Emb, 5)
    print(Ans)
    for a in Ans:
        display_image(a)
    time.sleep(5)
    MemorySnapshot, ImageName = GetMemory()
    JsonData.SaveJson("Data.json",ImageName,MemorySnapshot)

