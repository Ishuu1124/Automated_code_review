import os
import time
import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from models.granite_model import query_granite
from utils.chunker import chunk_text
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
def run_simple_rag(tf_text: str) -> dict:
    start_time = time.time()
    review_chunks = chunk_text(tf_text, max_tokens=200)
    all_chunk_feedback = []
    corrected_chunks = []
    rolling_context_window = 2
    running_summary = []
    for i, chunk in enumerate(review_chunks):
        # Rolling memory of previous chunks
        start = max(i - rolling_context_window, 0)
        previous_chunks = review_chunks[start:i]
        contextual_chunk = "\n".join(previous_chunks + [chunk])
        # Embedding + semantic retrieval
        embedding = model.encode([contextual_chunk])[0]
        context_docs = get_top_k_chunks(embedding, k=20)
        context = "\n---\n".join([doc[2] for doc in context_docs])
        summary_section = "\n".join(running_summary[-5:])
        # REVIEW PROMPT
        review_prompt = f"""You are an expert Terraform code reviewer focused on enforcing internal standards for `variables.tf` files used in IBM Cloud infrastructure.
So far, the review has identified these issues:
{summary_section if summary_section else "No issues found yet."}
Analyze the following chunk of a `variables.tf` file. Identify any new issues according to these rules:
- Hardcoded values or secrets
- Incorrect or overly broad data types (e.g., using `string` instead of `bool`)
- Missing or weak validations
- Naming convention violations
- Ordering issues — required variables must appear at the top
- Avoid any feedback on variable descriptions
- Do not summarize key variables
Relevant context:
{context}
Terraform code to review:
{contextual_chunk}
Answer:"""
        review_response = query_granite(review_prompt)
        all_chunk_feedback.append((i, review_response))
        running_summary.append(review_response)
        # FIX PROMPT
        fix_prompt = f"""You are a Terraform expert. Here is a chunk of a `variables.tf` file that may contain issues.
Your job is to correct the code by fixing:
- Hardcoded values or secrets
- Incorrect or broad types
- Missing or weak validation blocks
- Naming convention issues
- Ordering (required vars should come first)
Do not change variable descriptions. Keep structure clean and concise.
Context:
{context}
Code to fix:
{contextual_chunk}
Corrected Code:"""
        fix_response = query_granite(fix_prompt)
        corrected_chunks.append(fix_response)
    # FINAL REVIEW SYNTHESIS
    feedbacks = "\n\n".join([f"Chunk {i}:\n{resp}" for i, resp in all_chunk_feedback])
    final_prompt = f"""You are a Terraform code review summarizer.
Here are feedbacks from reviewing each chunk of a `variables.tf` file. Now write a final, consolidated review that:
- Merges all the issues found
- Removes duplicates
- Highlights patterns
- Organizes issues cleanly
Chunk feedback:
{feedbacks}
Final Review:"""
    final_review = query_granite(final_prompt)
    final_code = "\n\n".join(corrected_chunks)
    end_time = time.time()
    print(f"Granite full review + fix took {end_time - start_time:.2f} seconds.")
    return {
        "final_review": final_review,
        "corrected_code": final_code
    }