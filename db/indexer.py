import os
import psycopg
import time
import hashlib
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import glob

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

print("DB_NAME:", DB_NAME)
print("DB_USER:", DB_USER)

DB_CONN = f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} host={DB_HOST} port={DB_PORT}"
DATA_DIR = "data"
model = SentenceTransformer("all-MiniLM-L6-v2")

def connect_db():
    return psycopg.connect(DB_CONN)

def init_db(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("""
                CREATE TABLE IF NOT EXISTS docs (
                id SERIAL PRIMARY KEY,
                path TEXT UNIQUE,
                content TEXT,
                content_hash TEXT,
                embedding vector(384)
            );
        """)
        conn.commit()

def hash_content(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def index_docs(folder=DATA_DIR):
    start_time = time.time()
    conn = connect_db()
    init_db(conn)

    files = glob.glob(os.path.join(folder, "*.txt")) + glob.glob(os.path.join(folder, "*.tf"))
    updated_count = 0

    with conn.cursor() as cur:
        for path in files:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            content_hash = hash_content(content)
            
            cur.execute("SELECT content_hash FROM docs WHERE path = %s", (path,))
            row = cur.fetchone()
            if row and row[0] == content_hash:
                print(f"Skipped (no change): {path}")
                continue
            embedding = model.encode(content).tolist()
            cur.execute("""
                INSERT INTO docs (path, content, content_hash, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (path) DO UPDATE
                SET content = EXCLUDED.content,
                    content_hash = EXCLUDED.content_hash,
                    embedding = EXCLUDED.embedding
            """, (path, content, content_hash, embedding))
            conn.commit()
            updated_count += 1
            print(f"Indexed: {path}")
    conn.close()
    end_time = time.time()
    duration = end_time - start_time
    print(f"\nTotal files: {len(files)}")
    print(f"Files updated/indexed: {updated_count}")
    print(f"Indexing took {duration:.2f} seconds.")

if __name__ == "__main__":
    index_docs()