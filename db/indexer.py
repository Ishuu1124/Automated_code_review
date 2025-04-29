import os
import sys
import time
import glob
import hashlib
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.chunker import chunk_text
from db.pgvector_conn import get_pgvector_connection

load_dotenv()
DATA_DIR = "guide"
model = SentenceTransformer("all-MiniLM-L6-v2")

def init_db(conn):
    with conn.cursor() as cur:

        cur.execute("""
            CREATE EXTENSION IF NOT EXISTS vector;
            CREATE TABLE IF NOT EXISTS docs (
                id SERIAL PRIMARY KEY,
                path TEXT,
                chunk_index INT,
                content TEXT,
                content_hash TEXT,
                embedding vector(384),
                UNIQUE(path, chunk_index)
            );
        """)
        conn.commit()

def index_docs(folder=DATA_DIR):
    start_time = time.time()
    conn = get_pgvector_connection()
    init_db(conn)

    files = glob.glob(os.path.join(folder, "*.txt")) + glob.glob(os.path.join(folder, "*.tf"))
    total_files = len(files)
    updated_chunks = 0
    with conn.cursor() as cur:
        for path in files:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            chunks = chunk_text(content)
            embeddings = model.encode(chunks, batch_size=32, show_progress_bar=True)
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                content_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
                cur.execute("SELECT content_hash FROM docs WHERE path = %s AND chunk_index = %s", (path, i))
                row = cur.fetchone()
                if not row or row[0] != content_hash:
                    cur.execute("""
                        INSERT INTO docs (path, chunk_index, content, content_hash, embedding)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (path, chunk_index) DO UPDATE SET
                            content = EXCLUDED.content,
                            content_hash = EXCLUDED.content_hash,
                            embedding = EXCLUDED.embedding;
                    """, (path, i, chunk, content_hash, embedding.tolist()))
                    updated_chunks += 1
        conn.commit()

    conn.close()
    end_time = time.time()
    print(f"\nTotal files scanned: {total_files}")
    print(f"Chunks updated/indexed: {updated_chunks}")
    print(f"Indexing took {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    index_docs()