from src.rag.embeddings.embedding_model import (
    generate_embedding,
    generate_embeddings
)

if __name__ == "__main__":
    print("="*60)
    print("Embedding Test:")
    print("="*60)

    #Test 1 : Single Text
    text = "Climate change is causing rising global tempeature."
    embedding = generate_embedding(text)

    print("\nSingle embeddings:")
    print(f"Vector type:{type(embedding)}")
    print(f"Vector dimensions:{len(embedding)}")
    print(f"First five values:{embedding[:5]}")

    #Test 2 : Multiple chunks.
    texts = ["Climate change is casing rising temperature."
             "Canada is experiencing changes is extreme wheather conditions."
             "Heavy rainfall can increase the risk of flooding."
    ]
    embeddings = generate_embeddings(texts)
    print("\nBatch embeddings:")
    print(f"Number of texts:{len(texts)}")
    print(f"Number of embeddings:{len(embeddings)}")
    print(f"Embedding dimensions:{len(embeddings)}")
    print(f"First five values:{embeddings[:5]}")

    #Validation
    print("\n"+"="*60)
    print("Validation:")
    print("="*60)

    if len(embeddings) == 384:
        print("Embedding dimensions is correct: 384")
    else:
        print(f"Unexpected dimensions:{len(embeddings)}")

    if len(embeddings) == len(texts):
        print("All texts generated embeddings.")
    else:
        print("Embedding count mismatch.")

    print("\n"+"="*60)
    print("Embedding test completed.")
    print("="*60)


    
