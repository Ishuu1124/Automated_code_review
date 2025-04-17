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

def get_context_from_db(tf_content, top_k=3):
    embedding = embedder.encode(tf_content).tolist()
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
    return f"""You are an expert Terraform code reviewer.
Below are Terraform best practices and reference examples. Your task is to analyze the given `variables.tf` file and identify **any mistakes, anti-patterns, or violations of best practices**.
Be strict and highlight:
- Hardcoded values or secrets
- Wrong data types (e.g., string instead of bool)
- Lack of validations
- Any other Terraform or IBM Cloud-specific issues
- Do not give any changes or suggestions regarding variable description for now
Context:
{context_snippets}

---

Code to review:
{tf_content}

---

Please list all the issues and provide recommendations:"""

def run_simple_rag(tf_text: str):
    context_docs = get_context_from_db(tf_text, top_k=3)
    prompt = build_prompt(context_docs, tf_text)

    return query_granite(prompt)
