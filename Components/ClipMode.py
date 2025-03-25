from sentence_transformers import SentenceTransformer, util
from PIL import Image
import numpy as np
import torch

# Automatically select device (GPU if available, else CPU)
device = "cuda" if torch.cuda.is_available() else "cpu"
# device = "cpu"

# Load model on the selected device
model = SentenceTransformer('clip-ViT-L-14', device=device)

def TextEmb(Text, model=model):
    try:
        return model.encode(Text, device=device)
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print("⚠️ Out of memory! Switching to CPU...")
            torch.cuda.empty_cache()  # Free up VRAM
            model.to("cpu")  # Move model to CPU
            return model.encode(Text, device="cpu")  # Retry on CPU
        else:
            raise  # Re-raise other errors

def ImgEmb(Img, model=model):
    try:
        img = Image.open(Img).convert("RGB")  # Ensure image is RGB
        return model.encode(img, device=device)
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print("⚠️ Out of memory! Switching to CPU...")
            torch.cuda.empty_cache()
            model.to("cpu")
            return model.encode(img, device="cpu")
        else:
            raise

def CosSemilarity(Emb1, Emb2):
    cos_scores = util.cos_sim(Emb1, Emb2)
    return cos_scores.item()

def DotSemilarity(Emb1, Emb2):
    cos_scores = util.dot_score(Emb1, Emb2)
    return cos_scores.item()


def create_query_embedding(Emb, 
                           positive_texts="", negative_texts="",
                           positive_images="", negative_images="",
                           posTextWeight=1.0, negTextWeight=1.0,
                           posImgWeight=1.0, negImgWeight=1.0, safeMode = False):
    """
    Create a combined query embedding by adjusting a base embedding using
    positive/negative texts and positive/negative images.
    
    For text inputs, embeddings are computed via TextEmb().
    For image inputs, each provided string is converted to a file path by
    prepending "CapturedData\Snap - " and appending ".jpg", then ImgEmb() is used.
    
    The weighted contributions from positive sources are added while those
    from negative sources are subtracted.
    
    Parameters:
        Emb (numpy.ndarray): The base embedding.
        positive_texts (str): Comma-separated positive text inputs.
        negative_texts (str): Comma-separated negative text inputs.
        positive_images (str): Comma-separated positive image descriptors.
        negative_images (str): Comma-separated negative image descriptors.
        posTextWeight (float): Weight for positive text embeddings.
        negTextWeight (float): Weight for negative text embeddings.
        posImgWeight (float): Weight for positive image embeddings.
        negImgWeight (float): Weight for negative image embeddings.
        SafeMode (bool) : if True, negative texts will be "" (empty)
    
    Returns:
        numpy.ndarray: The final, normalized embedding.
    """
    
    # Start with a copy of the base embedding
    combined = Emb.copy()
    
    # Process positive texts
    if positive_texts:
        pos_text_list = [txt.strip() for txt in positive_texts.strip().split(",") if txt.strip()]
        print(f"Postive Texts are {positive_texts}")
        if pos_text_list:
            pos_text_embs = [TextEmb(txt) for txt in pos_text_list]
            avg_pos_text_emb = np.mean(pos_text_embs, axis=0) * posTextWeight
            combined += avg_pos_text_emb
    
    # Process negative texts (subtract their contribution)
    if negative_texts or safeMode == True: 
        if safeMode:
            negative_texts = [""]
            neg_emb = negTextWeight * model.encode("")
            combined -= neg_emb

        else:
            neg_text_list = [txt.strip() for txt in negative_texts.strip().split(",") if txt.strip()]
            print(f"Neg Texts are {neg_text_list}, Neg Weight = {negTextWeight}")
            if neg_text_list:
                neg_text_embs = [TextEmb(txt) for txt in neg_text_list]
                avg_neg_text_emb = np.mean(neg_text_embs, axis=0) * negTextWeight
                combined -= avg_neg_text_emb
            
    # Process positive images
    if positive_images:
        pos_img_list = [img.strip() for img in positive_images.strip().split(",") if img.strip()]
        print(f"Pos images are {positive_images}, pos Weight = {posImgWeight}")
        if pos_img_list:
            # Construct file paths for images and compute their embeddings
            pos_img_paths = [f"CapturedData\Snap-{img}.jpg" for img in pos_img_list]
            print(f" Positive Image list - {pos_img_paths}")
            pos_img_embs = [ImgEmb(path) for path in pos_img_paths]
            avg_pos_img_emb = np.mean(pos_img_embs, axis=0) * posImgWeight
            combined += avg_pos_img_emb
    
    # Process negative images (subtract their contribution)
    if negative_images:
        neg_img_list = [img.strip() for img in negative_images.strip().split(",") if img.strip()]
        print(f"neg images are {negative_images}, pos Weight = {negImgWeight}")
        if neg_img_list:
            neg_img_paths = [f"CapturedData\Snap-{img}.jpg" for img in neg_img_list]
            print(f" Negative Image list - {neg_img_paths}")
            neg_img_embs = [ImgEmb(path) for path in neg_img_paths]
            avg_neg_img_emb = np.mean(neg_img_embs, axis=0) * negImgWeight
            combined -= avg_neg_img_emb
    
    # Normalize the final combined embedding to unit length
    norm = np.linalg.norm(combined)
    if norm > 0:
        combined = combined / norm
    print(f"Old embedding is - {Emb}")
    print(f"New embedding is - {combined}")
        
    return combined

def create_query_embeddingOld(positive_terms, negative_terms, posW =1.0, negW =1.0,
                           pos_weights=None, neg_weights=None, model=model):
    """
    Create a mixed embedding by combining positive and negative text embeddings.
    
    Parameters:
        positive_terms (list of str): Texts describing desired attributes (e.g., ["girl in white dress"]).
        negative_terms (list of str): Texts describing undesired attributes (e.g., ["guy", "porn"]).
        pos_weights (list of float, optional): Weights for positive terms (defaults to 1.0 each).
        neg_weights (list of float, optional): Weights for negative terms (defaults to 1.0 each).
        model (SentenceTransformer, optional): The model to use for generating embeddings.
    
    Returns:
        numpy.ndarray: The normalized combined query embedding.
    """
    # Set default weights if not provided
    if pos_weights is None:
        pos_weights = [posW/len(positive_terms)] * len(positive_terms)
    if neg_weights is None:
        neg_weights = [negW/len(negative_terms)] * len(negative_terms)
    
    # Compute weighted embeddings for positive terms
    pos_emb = np.sum([w * model.encode(term) for term, w in zip(positive_terms, pos_weights)], axis=0)
    # Compute weighted embeddings for negative terms
    neg_emb = np.sum([w * model.encode(term) for term, w in zip(negative_terms, neg_weights)], axis=0)
    
    # Combine by subtracting negatives from positives
    query_emb = pos_emb - neg_emb
    
    # Normalize the combined embedding to unit length
    norm = np.linalg.norm(query_emb)
    if norm > 0:
        query_emb = query_emb / norm
    
    return query_emb


def combine_embeddings(emb1, emb2, weight1=0.5, weight2=0.5):
    """
    Combine two embeddings with specified weights.
    
    Parameters:
        emb1 (numpy.ndarray): First embedding vector.
        emb2 (numpy.ndarray): Second embedding vector.
        weight1 (float): Scalar weight for emb1 (default is 1.0).
        weight2 (float): Scalar weight for emb2 (default is -1.0).
            For example, passing weight1=1 and weight2=-0.7 produces a combination
            equal to emb1 - 0.7 * emb2 (then normalized).
    
    Returns:
        numpy.ndarray: The normalized combined embedding.
    """
    # Multiply each embedding by its weight and add them together
    combined = weight1 * emb1 + weight2 * emb2
    
    # Normalize the result to have unit length
    norm = np.linalg.norm(combined)
    if norm > 0:
        combined = combined / norm
    return combined

if __name__ == "__main__":

    print("Hii")

    Sentence = "Anything_To_Test"
    Sentence2 = "Anything_To_Test"
    Sentence3 = "Anything_To_Test"
    Sentence4 = "Anything_To_Test"


    emb1 = TextEmb(Sentence)
    emb2 = TextEmb(Sentence2)
    emb3 = TextEmb(Sentence3)
    emb4 = TextEmb(Sentence4)

    while True:
        text = input("Enter Text: ")
        embNew = TextEmb(text)
        print(f"Cos Similarty with {Sentence}: {CosSemilarity(embNew, emb1)}")
        print(f"Cos Similarty with {Sentence2}: {CosSemilarity(embNew, emb2)}")
        print(f"Cos Similarty with {Sentence3}: {CosSemilarity(embNew, emb3)}")
        print(f"Cos Similarty with {Sentence4}: {CosSemilarity(embNew, emb4)}")
        print("\n")
        print("\n")

        print(f"Dot Similarty with {Sentence}: {DotSemilarity(embNew, emb1)}")
        print(f"Dot Similarty with {Sentence2}: {DotSemilarity(embNew, emb2)}")
        print(f"Dot Similarty with {Sentence3}: {DotSemilarity(embNew, emb3)}")
        print(f"Dot Similarty with {Sentence4}: {DotSemilarity(embNew, emb4)}")

        print("\n")

