
from src.rag.vector_db.qdrant_client import client, COLLECTION_NAME


def main():

    print("=" * 60)
    print("QDRANT STORAGE VERIFICATION")
    print("=" * 60)

    # --------------------------------------------------
    # 1. Check collection
    # --------------------------------------------------

    print("\n1. Checking collection...")

    collections = client.get_collections().collections

    collection_names = [
        collection.name for collection in collections
    ]

    if COLLECTION_NAME not in collection_names:
        print(f"ERROR: Collection '{COLLECTION_NAME}' not found.")
        return

    print(f"Collection '{COLLECTION_NAME}' exists.")

    # --------------------------------------------------
    # 2. Check total stored points
    # --------------------------------------------------

    print("\n2. Checking stored points...")

    collection_info = client.get_collection(
        collection_name=COLLECTION_NAME
    )

    total_points = collection_info.points_count

    print(f"Total points stored: {total_points}")

    if total_points == 0:
        print("ERROR: Collection is empty.")
        return

    # --------------------------------------------------
    # 3. Retrieve all points using pagination
    # --------------------------------------------------

    print("\n3. Scanning stored documents...")

    all_points = []
    offset = None

    while True:

        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        all_points.extend(points)

        if next_offset is None:
            break

        offset = next_offset

    print(f"Total points scanned: {len(all_points)}")

    # --------------------------------------------------
    # 4. Identify unique documents
    # --------------------------------------------------

    print("\n4. Checking indexed documents...")

    document_counts = {}
    missing_metadata = 0

    for point in all_points:

        payload = point.payload or {}

        document_name = payload.get("document_name")

        if not document_name:
            missing_metadata += 1
            document_name = "UNKNOWN DOCUMENT"

        document_counts[document_name] = (
            document_counts.get(document_name, 0) + 1
        )

    print("\nDocument-wise indexing details:")
    print("-" * 60)

    for document_name, count in sorted(document_counts.items()):

        print(f"Document: {document_name}")
        print(f"Chunks  : {count}")
        print("-" * 60)

    print(f"\nUnique documents found: {len(document_counts)}")

    if missing_metadata > 0:
        print(
            f"WARNING: {missing_metadata} points have no document name."
        )

    # --------------------------------------------------
    # 5. Retrieve sample point
    # --------------------------------------------------

    print("\n5. Retrieving sample point...")

    if all_points:

        point = all_points[0]
        payload = point.payload or {}

        print("\nSample point details:")
        print("-" * 60)

        print(f"Point ID       : {point.id}")
        print(f"Document Name  : {payload.get('document_name')}")
        print(f"Document ID    : {payload.get('document_id')}")
        print(f"Chunk ID       : {payload.get('chunk_id')}")
        print(f"Page Number    : {payload.get('page')}")
        print(f"Character Count: {payload.get('char_count')}")

        text = payload.get("text", "")

        print("\nText Preview:")
        print("-" * 60)
        print(text[:500])

        if len(text) > 500:
            print("...")

        print("-" * 60)

    # --------------------------------------------------
    # 6. Final summary
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("QDRANT VERIFICATION SUMMARY")
    print("=" * 60)

    print(f"Collection       : {COLLECTION_NAME}")
    print(f"Total Points     : {total_points}")
    print(f"Points Scanned   : {len(all_points)}")
    print(f"Unique Documents : {len(document_counts)}")
    print(f"Missing Metadata : {missing_metadata}")

    print("\nQDRANT VERIFICATION COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()