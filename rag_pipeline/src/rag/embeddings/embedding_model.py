from sentence_transformers import SentenceTransformer

# UPDATED : Centralise embedding model
MODEL_NAME = "all-MiniLM-L6-v2"

#UPDATED : Load the model once 
model = SentenceTransformer(MODEL_NAME)

def generate_embedding(text:str) -> list[float]:
    """
    Generate an embeddings vector for a single text chunk.

    Args:
        text : Text to convert into an embeddings.
    Returns:
        Embeddings vector as the list of floats.
    """

    if not text :
        raise ValueError("Text cannot be empty.")

    # UPDATED : Generate embeddings in batch
    embeddings = model.encode(text)

    # UPDATED : convert numpy array to python list 
    return embeddings.tolist()

def generate_embeddings(texts:list[str]) -> list[list[float]]:
    """
    Generate the embeddings for the multiple text chunks.
    
    Args:
        texts : List of text chunks.
    Returns:
        List of embedding vectors.
    """
    if not texts :
        return []

    # UDATED : Generate embeddings in batch.
    embeddings = model.encode(texts)

    # UPDATED : Convert to normal python list
    return embeddings.tolist()




