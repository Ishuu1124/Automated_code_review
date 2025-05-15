import os
import re
import time
import numpy as np
import psycopg
from dotenv import load_dotenv
from pymilvus import Collection, utility
from models.granite_model import query_granite, embed_text
from utils.chunker import chunk_text


load_dotenv()

MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

def extract_renamed_vars(review_text: str) -> list[tuple[str, str]]:
    pattern = r'`?(\w+)`?\s*->\s*`?(\w+)`?'
    return re.findall(pattern, review_text)

def extract_validation_blocks(text: str) -> dict:
    variable_blocks = re.findall(r'(variable\s+"[^"]+"\s*{[^}]*?(validation\s*{[^}]*}[^}]*?)+})', text, re.DOTALL)
    return {
        re.search(r'variable\s+"([^"]+)"', block[0]).group(1): block[0]
        for block in variable_blocks if re.search(r'variable\s+"([^"]+)"', block[0])
    }

def reinsert_validation_blocks(original: str, fixed: str) -> str:
    original_blocks = extract_validation_blocks(original)
    for var_name, original_block in original_blocks.items():
        fixed = re.sub(
            rf'(variable\s+"{re.escape(var_name)}"\s*{{)(.*?)(}})',
            lambda m: original_block,
            fixed,
            flags=re.DOTALL
        )
    return fixed

def get_pgvector_connection():
    return psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def get_top_k_chunks(query_embedding, k=20, filter_by_filename="variables.tf"):
    conn = get_pgvector_connection()
    with conn.cursor() as cur:
        sql = """
            SELECT path, chunk_index, content, content_hash, embedding
            FROM docs
        """
        if filter_by_filename:
            sql += f" WHERE path LIKE '%%{filter_by_filename}'"
        sql += " ORDER BY embedding <-> %s::vector LIMIT %s"
        cur.execute(sql, (query_embedding.tolist(), k))
        context_chunks = cur.fetchall()
    conn.close()
    return context_chunks

def run_simple_rag(tf_text: str) -> dict:
    start_time = time.time()
    review_chunks = chunk_text(tf_text, file_type="tf")
    print(f"[INFO] Total review chunks: {len(review_chunks)}")
    all_chunk_feedback = []
    corrected_chunks = []
    running_summary = []
    renamed_variables = []
    best_practices = load_best_practices()

    for i, chunk in enumerate(review_chunks):
        print(f"\n[INFO] Processing chunk {i + 1}/{len(review_chunks)}")
        try:
            embedding = np.array(embed_text(chunk))
            context_docs = get_top_k_chunks(embedding, 5)
            context = "\n---\n".join([doc[2] for doc in context_docs])
            summary_section = "\n".join(running_summary[-5:]) or "No issues found yet."

            review_prompt = REVIEW_PROMPT_TEMPLATE.format(
                best_practices=best_practices,
                summary_section=summary_section,
                chunk=chunk
            )
            review_response = query_granite(review_prompt).strip()
            if review_response and not review_response.startswith("[Error"):
                print(f"[INFO] Review response for chunk {i+1}: {review_response}")
                renamed_variables.extend(extract_renamed_vars(review_response))
            else:
                print(f"[ERROR] No valid review response for chunk {i+1}")
            all_chunk_feedback.append((i+1, review_response))
            running_summary.append(review_response)
        except Exception as e:
            print(f"[ERROR] Review failed for chunk {i+1}: {e}")
            all_chunk_feedback.append((i+1, "[ERROR] Review failed"))
            continue

        try:
            fix_prompt = FIX_PROMPT_TEMPLATE.format(context=context, chunk=chunk)
            fix_response = query_granite(fix_prompt).strip()
            fixed_with_validation = reinsert_validation_blocks(chunk, fix_response)
            corrected_chunks.append(fixed_with_validation)
        except Exception as e:
            print(f"[ERROR] Fix failed for chunk {i+1}: {e}")
            corrected_chunks.append(chunk)

    feedbacks = "\n\n".join([f"Chunk {i}:\n{resp}" for i, resp in all_chunk_feedback])

    try:
        if renamed_variables:
            unique_renames = sorted(set(renamed_variables))
            rename_table_rows = "\n".join(
                f"| `{old}` | `{new}` |" for old, new in unique_renames if old != new
            )
        else:
            rename_table_rows = "_No renaming suggestions found._"

        final_prompt = FINAL_PROMPT_TEMPLATE.format(
            chunk_summaries=feedbacks,
            rename_table=rename_table_rows
        )
        final_review = query_granite(final_prompt).strip()
        print(f"[INFO] Review response: {final_review}")
    except Exception as e:
        print(f"[ERROR] Final review synthesis failed: {e}")
        final_review = "[ERROR] Could not generate consolidated review."

    final_code = "\n\n".join(corrected_chunks)
    print(f"\n[INFO] Granite full review + fix took {time.time() - start_time:.2f} seconds.")

    return {
        "final_review": final_review,
        "corrected_code": final_code
    }


def load_best_practices():
    best_practices = ""
    guide_folder = os.getenv("GUIDE_FOLDER_PATH")
    for filename in os.listdir(guide_folder):
        if filename.endswith(".txt"):
            with open(os.path.join(guide_folder, filename), "r") as file:
                best_practices += file.read() + "\n---\n"
    return best_practices

REVIEW_PROMPT_TEMPLATE = """You are an expert Terraform code reviewer focused on enforcing IBM Cloud standards for `variables.tf`.
Apply the following internal best practices:
{best_practices}

So far, the review has identified these issues:
{summary_section}

Analyze this Terraform code chunk and provide structured feedback also strictly follow these rules while renaming the variables:
- Use `snake_case` for all variable names.
- Expand non-standard abbreviations (e.g., sm → secrets_manager).
- Preserve standard acronyms (`vpc`, `cos`, `kms`, `crn`).
- Boolean variables must begin with `enable_`, `disable_`, or `use_`.
- Suffix variable names with `_id`, `_name`, `_crn`, etc. where applicable.
- Prefix with `existing_` if referencing an existing resource.
- Group all `existing_*` variables before new ones.
- Do NOT touch `validation` blocks.
- Do NOT reword or paraphrase `description` fields.
- Do NOT explain anything — output only the corrected code, no extra text.
Respond only in bullet points.

Terraform code chunk:
{chunk}
"""

FIX_PROMPT_TEMPLATE = """You are a Terraform expert improving a `variables.tf` chunk to meet IBM Cloud naming standards.

Strictly follow these rules:
- Use `snake_case` for all variable names.
- Expand non-standard abbreviations (e.g., sm → secrets_manager).
- Preserve standard acronyms (`vpc`, `cos`, `kms`, `crn`).
- Boolean variables must begin with `enable_`, `disable_`, or `use_`.
- Suffix variable names with `_id`, `_name`, `_crn`, etc. where applicable.
- Prefix with `existing_` if referencing an existing resource.
- Group all `existing_*` variables before new ones.
- Do NOT touch `validation` blocks.
- Do NOT reword or paraphrase `description` fields.
- Do NOT explain anything — output only the corrected code, no extra text.

Context:
{context}

Terraform code chunk:
{chunk}

Corrected Code:
"""


FINAL_PROMPT_TEMPLATE = """You are synthesizing a complete review of a Terraform `variables.tf` file based on chunk-level feedback and corrections.

Generate the following:

1. **Summary (2–3 sentences)**:
Summarize the main issues identified across all chunks (naming, structure, clarity). Avoid repetition.

2. **Renamed Variables Table**:
Provide a Markdown table of variables that were renamed, based on chunk-level suggestions.

Only include variables that were actually renamed.

| Current Variable Name | Suggested Variable Name |
|-----------------------|--------------------------|
{rename_table}

---

Below is the full review data from chunk analysis:

{chunk_summaries}

Final Output:
"""