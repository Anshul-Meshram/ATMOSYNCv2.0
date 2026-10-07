
from src.rag.retrieval.retriever import retrieve_chunks
from .retrieval_evaluation import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

def main():
    print("-"*70)
    print("RAG Retrieval Evaluation Test")
    print("="*70)

    query = "What are the major climate changes discussed in canada?"

    print(f"\nQuery: {query}")

    #Retreive relevant candidates
    results = retrieve_chunks(query, top_k = 5)

    retrieved_ids = [
        result["chunk_id"]
        for result in results
        if result["chunk_id"]
    ]

    print("\nRetrieved Chunks with context:")
    print("-"*70)
    for rank , result in enumerate(results,start =1):
        print(f"\nRank: {rank}")
        print(f"Chunk_ID: {result['chunk_id']}")
        print(f"Document: {result['document_name']}")
        print(f"Page:{result['page']}")
        print(f"Similarity Score:{result['score']:.4f}")
        print(f"Text:\n{result['text'][:700]}")
        print("-"*70)

    #Temporary ground truth
    #Replace these example IDs with actual relecant chunk IDs identified by manually reading the chunks.

    relevant_ids = relevant_ids = {
    "Climate_Intelligence_System_Project_Report_page_3_chunk_1"
}

    if not relevant_ids:
        print("\nGround truth is not configured yet.")
        print("Read the retrieved chunks and identify relevant IDs.")
        return
    k = 5

    print("\nRelevant IDs:")
    print(relevant_ids)

    print("\nRetrieved IDs:")
    print(retrieved_ids)

    precision = precision_at_k(
        retrieved_ids,
        relevant_ids,
        k
    )
    recall = recall_at_k(
        retrieved_ids,
        relevant_ids,
        k
    )

    mrr = reciprocal_rank(
        retrieved_ids,
        relevant_ids,
    )

    print("\n"+"-"*70)
    print("Evaluation Results")
    print("-"*70)

    print(f"Precison@{k}:{precision: .4f}")
    print(f"Recall@{k}:{recall: .4f}")
    print(f"MRR:{mrr: .4f}")
    print("\nEvaluation Completed.")

if __name__ == "__main__":
    main()