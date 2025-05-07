import os
import time
import glob
import hashlib
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from pymilvus import Collection, connections
from utils.chunker import chunk_text
from db.milvus_conn import connect_milvus, init_milvus, COLLECTION_NAME

load_dotenv()
DATA_DIR = "guide"
model = SentenceTransformer("all-MiniLM-L6-v2")

def index_docs(folder=DATA_DIR):
    start_time = time.time()
    connect_milvus()
    init_milvus()
    collection = Collection(COLLECTION_NAME)

    files = glob.glob(os.path.join(folder, "*.txt")) + glob.glob(os.path.join(folder, "*.tf"))
    total_files = len(files)
    updated_chunks = 0

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        chunks = chunk_text(content)
        embeddings = model.encode(chunks, batch_size=32, show_progress_bar=True)
        to_insert = {"path": [], "chunk_index": [], "content": [], "content_hash": [], "embedding": []}

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            content_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()

            expr = f'path == "{path}" && chunk_index == {i}'
            collection.load()
            results = collection.query(expr, output_fields=["content_hash"])

            if not results or results[0]["content_hash"] != content_hash:
                to_insert["path"].append(path)
                to_insert["chunk_index"].append(i)
                to_insert["content"].append(chunk)
                to_insert["content_hash"].append(content_hash)
                to_insert["embedding"].append(embedding.tolist())
                updated_chunks += 1

        if to_insert["path"]:
            collection.insert([to_insert["path"], to_insert["chunk_index"], to_insert["content"], to_insert["content_hash"], to_insert["embedding"]])

    end_time = time.time()
    print(f"\nTotal files scanned: {total_files}")
    print(f"Chunks updated/indexed: {updated_chunks}")
    print(f"Indexing took {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    index_docs()
