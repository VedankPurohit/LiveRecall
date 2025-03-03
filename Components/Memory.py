import Components.ClipMode as ClipMode
import torch
import time
import Components.JsonData as JsonData
def TimeField():
    return time.strftime("%y%m%d%H%M%S")


ImageNames, MemorySnapShot, TimeLine = JsonData.LoadJson("Data.json")

print(len(MemorySnapShot), len(ImageNames), len(TimeLine))



def AddToMemory(Image):
    Embedding = ClipMode.ImgEmb(Image)
    MemorySnapShot.append(Embedding)
    ImageNames.append(Image)
    TimeLine.append(TimeField())
    return True

def AutoAddMemory(CaptureImage, cap, Timer, MaxBufferSize):
    BufferSize = 0
    while True:
        if BufferSize > MaxBufferSize:
            BufferSize = 0
            MemorySnapShot = MemorySnapShot[:MaxBufferSize]
            ImageNames = ImageNames[:MaxBufferSize]
        time.sleep(Timer)
        Location = f"Vision AI\Temp\Image{BufferSize}.png"
        CaptureImage.ClearestImg(1,200,cap=cap, image=Location)
        AddToMemory(Location)




def GetMemory():
    return MemorySnapShot, ImageNames, TimeLine

def ClearMemory():
    MemorySnapShot = []
    ImageNames = []
    TimeLine = []
    return True

def RetriveMemory(Embedding):
    Semilarity = ClipMode.DotSemilarity(Embedding, MemorySnapShot)
    Index = torch.argmax(Semilarity)
    return ImageNames[Index], Semilarity


def RetriveMemoryMax(Embedding, Number):
    Semilarity = ClipMode.DotSemilarity(Embedding, MemorySnapShot)
    values, Indexs = torch.topk(Semilarity, Number)
    print(Indexs)
    Lis = []
    for Index in Indexs[0]:
        if isinstance(Index.item(), int):
            print(Index.item())
            Lis.append(ImageNames[Index.item()])

    if len(Lis) == 0:
        print("List returned 0?")
        Semilarity = ClipMode.CosSemilarity(Embedding, MemorySnapShot)
        values, Indexs = torch.topk(Semilarity, Number)
        print(Indexs)
        Lis = []
        for Index in Indexs[0]:
            if isinstance(Index.item(), int):
                print(Index.item())
                Lis.append(ImageNames[Index.item()])

    print("Retrived images count : ", + len(Lis))
    print(Lis)

    return Lis, Semilarity



if __name__ == "__main__":


    print(len(GetMemory()[0]))
    while True:
        Text = input("Enter Text: ")
        Emb = ClipMode.TextEmb(Text)
        print(RetriveMemory(Emb))