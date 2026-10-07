
from src.rag.retrieval.retriever import retrieve_chunks


def main():

    print("=" * 70)
    print("SOURCE-AWARE RETRIEVAL TEST")
    print("=" * 70)

    query = "What are the major climate changes discussed in Canada?"

    print(f"\nQuery: {query}")
    print("\nSearching Qdrant...")

    results = retrieve_chunks(query, top_k=5)

    print(f"\nRetrieved {len(results)} chunks.")

    for index, result in enumerate(results, start=1):

        print("\n" + "-" * 70)
        print(f"RESULT {index}")
        print("-" * 70)

        print(f"Similarity Score : {result['score']:.4f}")
        print(f"Document         : {result['document_name']}")
        print(f"Document ID      : {result['document_id']}")
        print(f"Chunk ID         : {result['chunk_id']}")
        print(f"Page Number      : {result['page']}")
        print(f"Character Count  : {result['char_count']}")

        print("\nRetrieved Context:")
        print(result["text"][:700])

        if len(result["text"]) > 700:
            print("...")

    print("\n" + "=" * 70)
    print("SOURCE-AWARE RETRIEVAL TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()