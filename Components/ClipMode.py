from sentence_transformers import SentenceTransformer, util
from PIL import Image

# model = SentenceTransformer('clip-ViT-B-32')
model = SentenceTransformer('clip-ViT-L-14')

def TextEmb(Text, model=model):
    
    text_emb = model.encode(Text)
    return text_emb

def ImgEmb(Img, model = model):
    img_emb = model.encode(Image.open(Img))
    return img_emb

def CosSemilarity(Emb1, Emb2):
    cos_scores = util.cos_sim(Emb1, Emb2)
    return cos_scores

def DotSemilarity(Emb1, Emb2):
    cos_scores = util.dot_score(Emb1, Emb2)
    return cos_scores



if __name__ == "__main__":
    img_emb = model.encode(Image.open(r'Example'))

    #Encode text descriptions
    text_emb = model.encode(['Two dogs in the snow', 'A cat on a table', 'A picture of London at night', "Bus stand", "arafed man in a coat talking on a cell phone next to a bus", "2 men standing in front of a blue bus", "Realme 11 pro", "Realme 11 pro plus"])

    #Compute cosine similarities 
    print(img_emb.shape, text_emb.shape)

    cos_scores = util.cos_sim(img_emb, text_emb)
    print(cos_scores)


