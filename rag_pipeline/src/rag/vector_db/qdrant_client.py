from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# QDRANT CONFIGURATION
COLLECTION_NAME = "climate_documents"
VECTOR_SIZE = 384
DISTANCE_METRIC = Distance.COSINE

# Store Qdrant data inside the project
PROJECT_ROOT = Path(__file__).resolve().parents[3]
QDRANT_PATH = PROJECT_ROOT / "qdrant_storage"

# CREATE QDRANT CLIENT
client = QdrantClient(path=str(QDRANT_PATH))

# CREATE COLLECTION
def create_collection():

    # Check whether collection already exists
    collections = client.get_collections().collections

    existing_collections = [
        collection.name
        for collection in collections
    ]

    if COLLECTION_NAME in existing_collections:
        print(f"Collection '{COLLECTION_NAME}' already exists.")
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=DISTANCE_METRIC,
        ),
    )

    print(f"Collection '{COLLECTION_NAME}' created successfully.")


# MAIN TEST
if __name__ == "__main__":

    print("=" * 60)
    print("QDRANT VECTOR DATABASE TEST")
    print("=" * 60)

    print(f"\nStorage path:")
    print(QDRANT_PATH)

    print("\nCreating collection...")

    create_collection()

    print("\nAvailable collections:")

    collections = client.get_collections().collections

    for collection in collections:
        print(f"- {collection.name}")

    print("\n" + "=" * 60)
    print("QDRANT TEST COMPLETED")
    print("=" * 60)