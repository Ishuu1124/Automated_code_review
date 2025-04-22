import os
import time
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
    return f"""You are an expert Terraform code reviewer focused on enforcing internal standards for `variables.tf` files used in IBM Cloud infrastructure.
Analyze the following `variables.tf` file and identify **mistakes, anti-patterns, or violations** of Terraform and IBM Cloud best practices. Be **strict** and focus only on:

- Hardcoded values or secrets
- Incorrect or overly broad data types (e.g., using `string` instead of `bool`)
- Missing or weak validations
- Naming convention violations (e.g., inconsistent or unclear variable names like `vpc_resource_tags`)
- Ordering issues — required variables must appear **at the top** of the file
- Avoid any feedback on variable **descriptions**
- Do not summary of the key variables
Keep your response **concise and actionable**, avoiding unnecessary explanation or repetition.

Context:
{context}

Terraform file to review:
{chunk}

Answer:"""

def run_simple_rag(tf_text: str) -> str:
    start_time = time.time()

    review_chunks = chunk_text(tf_text, max_tokens=200)

    all_responses = []
    for chunk in review_chunks:
        embedding = model.encode([chunk])[0]
        context_docs = get_top_k_chunks(embedding, k=20)
        prompt = build_prompt(context_docs, chunk)
        response = query_granite(prompt)
        all_responses.append(response)

    end_time = time.time()
    duration = end_time - start_time
    print(f"Granite response generation took {duration:.2f} seconds.")
    return "\n\n".join(all_responses)