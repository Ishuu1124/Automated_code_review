import os
import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from models.granite_model import query_granite

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

embedder = SentenceTransformer('all-MiniLM-L6-v2')

def get_context_from_db(tf_text, top_k=3):
    embedding = embedder.encode(tf_text).tolist()
    conn = connect_db()

    embedding_str = f"[{','.join(map(str, embedding))}]"

    with conn.cursor() as cur:
        cur.execute("""
            SELECT content, embedding <=> %s::vector AS distance
            FROM docs
            ORDER BY distance ASC
            LIMIT %s
        """, (embedding_str, top_k))

        results = cur.fetchall()

    conn.close()
    return [row[0] for row in results]

def build_prompt(context_docs, tf_content):
    context_snippets = "\n---\n".join(context_docs)
    return f"""You are a Terraform assistant. You are given a `variables.tf file and some Terraform best practices.
Suggest improvements or highlight issues in the provided code based on the context.

Context:
{context_snippets}

---

Code to review:
{tf_content}

---

Suggestions:"""

def run_simple_rag(tf_file_path):
    with open(tf_file_path, "r", encoding="utf-8") as f:
        tf_content = f.read()

    context_docs = get_context_from_db(tf_content, top_k=3)
    prompt = build_prompt(context_docs, tf_content)

    return query_granite(prompt)
