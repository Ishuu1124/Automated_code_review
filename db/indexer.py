import os
import psycopg
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
def connect_db():
    return psycopg.connect(DB_CONN)

DATA_DIR = "data"

model = SentenceTransformer("all-MiniLM-L6-v2")

def init_db(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS docs (
                id SERIAL PRIMARY KEY,
                path TEXT,
                content TEXT,
                embedding vector(384)
            );
            CREATE EXTENSION IF NOT EXISTS vector;
        """)
        conn.commit()

def index_docs(folder=DATA_DIR):
    txt_files = glob.glob(os.path.join(folder, "*.txt"))
    conn = connect_db()
    init_db(conn)

    with conn.cursor() as cur:
        for path in txt_files:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            embedding = model.encode(content).tolist()
            cur.execute(
                "INSERT INTO docs (path, content, embedding) VALUES (%s, %s, %s)", 
                (path, content, embedding)
            )
            conn.commit()
            conn.close()
            print("Documents indexed.")

if __name__ == "__main__":
    index_docs()