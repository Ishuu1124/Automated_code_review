import os
import time
import psycopg
from dotenv import load_dotenv
from utils.chunker import chunk_text
from models.granite_model import query_granite
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

def run_simple_rag(tf_text: str) -> str:
    start_time = time.time()
    review_chunks = chunk_text(tf_text, max_tokens=200)
    all_chunk_feedback = []
    rolling_context_window = 2
    running_summary = []
    for i, chunk in enumerate(review_chunks):
        start = max(i - rolling_context_window, 0)
        previous_chunks = review_chunks[start:i]
        contextual_chunk = "\n".join(previous_chunks + [chunk])
        embedding = model.encode([contextual_chunk])[0]
        context_docs = get_top_k_chunks(embedding, k=20)
        context = "\n---\n".join([doc[2] for doc in context_docs])
        summary_section = "\n".join(running_summary[-5:])
        prompt = f"""You are an expert Terraform code reviewer focused on enforcing internal standards for `variables.tf` files used in IBM Cloud infrastructure.
So far, the review has identified these issues:
{summary_section if summary_section else "No issues found yet."}
Analyze the following chunk of a `variables.tf` file. Identify any new issues according to these rules:
- Hardcoded values or secrets
- Incorrect or overly broad data types (e.g., using `string` instead of `bool`)
- Missing or weak validations
- Naming convention violations (e.g., inconsistent or unclear variable names like `vpc_resource_tags`)
- Ordering issues — required variables must appear **at the top** of the file
- Avoid any feedback on variable **descriptions**
- Do not summary of the key variables

Relevant context:
{context}

Terraform code to review:
{contextual_chunk}

Answer:"""
        response = query_granite(prompt)
        all_chunk_feedback.append((i, response))
        running_summary.append(response)
    feedbacks = "\n\n".join([f"Chunk {i}:\n{resp}" for i, resp in all_chunk_feedback])
    final_prompt = f"""You are a Terraform code review summarizer.
You've been given feedback from multiple chunks of a `variables.tf` file, each reviewed separately. Now, write a final, coherent review that:
- Consolidates all issues found across chunks
- Removes duplicate or overlapping comments
- Highlights patterns or systemic issues
- Presents the feedback in a clean, organized structure

Chunk feedback:
{feedbacks}

Final Review:"""
    final_review = query_granite(final_prompt)
    end_time = time.time()
    print(f"Granite full review took {end_time - start_time:.2f} seconds.")
    return final_review