import os
import psycopg
from dotenv import load_dotenv
from models.granite_model import query_granite
from utils.chunker import chunk_text
from sentence_transformers import SentenceTransformer

load_dotenv()
model = SentenceTransformer("all-MiniLM-L6-v2")

def get_pgvector_connection():
    return psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def get_top_k_chunks(query_embedding, k=20):
    conn = get_pgvector_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT path, chunk_index, content, content_hash, embedding
            FROM docs
            ORDER BY embedding <-> %s::vector
            LIMIT %s;
        """, (query_embedding.tolist(), k)) 
        context_chunks = cur.fetchall()
    conn.close()
    return context_chunks

def build_prompt(context_docs, chunk):
    context = "\n---\n".join([doc[2] for doc in context_docs])
    return f"""You are an expert Terraform code reviewer.
Below are Terraform best practices and reference examples. Your task is to analyze the given `variables.tf` file and identify **any mistakes, anti-patterns, or violations of best practices**.
Be strict and highlight:

- Hardcoded values or secrets
- Wrong data types (e.g., string instead of bool)
- Lack of validations
- Any other Terraform or IBM Cloud-specific issues
- Do not give any changes or suggestions regarding variable description for now

Context:
{context}

---

Code to review:
{chunk}

---

Identify any issues or misconfigurations:"""


def run_simple_rag(tf_text: str) -> str:

    review_chunks = chunk_text(tf_text, max_tokens=200)

    all_responses = []
    for chunk in review_chunks:
        embedding = model.encode([chunk])[0]
        context_docs = get_top_k_chunks(embedding, k=20)
        prompt = build_prompt(context_docs, chunk)
        response = query_granite(prompt)
        all_responses.append(response)

    return "\n\n".join(all_responses)
