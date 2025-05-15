import os
import time
import glob
import hashlib
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from pymilvus import Collection, connections
from utils.chunker import chunk_text
from db.dbFactory import dbFactory


load_dotenv()
DATA_DIR = "guide"
model = SentenceTransformer("all-MiniLM-L6-v2")


db = dbFactory.makedb("milvus")

def index_docs(folder=DATA_DIR):
    start_time = time.time()

    files = glob.glob(os.path.join(folder, "*.txt")) + glob.glob(os.path.join(folder, "*.tf"))
    total_files = len(files)
    updated_chunks = 0

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        ext = os.path.splitext(path)[1].lower()
        file_type = "tf" if ext == ".tf" else "txt"
        chunks = chunk_text(content, file_type=file_type)

        embeddings = model.encode(chunks, batch_size=32, show_progress_bar=True)
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            content_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
            db.add_index(path, i, chunk, content_hash, embedding)
            updated_chunks+=1
    
    db.close_conn()

    duration = time.time() - start_time
    print(f"[INFO] Indexed {total_files} files with {updated_chunks} updated chunks in {duration:.2f} seconds.")
