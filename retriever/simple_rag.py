import os
import re
import time
import numpy as np
from dotenv import load_dotenv
from pymilvus import Collection, utility
from models.granite_model import query_granite, embed_text
from utils.chunker import chunk_text

load_dotenv()

MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

def get_milvus_connection():
    try:
        if utility.has_collection(COLLECTION_NAME):
            print(f"Found collection {COLLECTION_NAME}")
        collection = Collection(COLLECTION_NAME)
    except Exception as e:
        print(f"[ERROR] Failed to load collection from Milvus: {e}")
    if not utility.has_collection(COLLECTION_NAME):
        print(f"[ERROR] Collection {COLLECTION_NAME} not found in Milvus!")
    return collection

def get_top_k_chunks(query_embedding, k=5):
    collection = get_milvus_connection()
    collection.load()
    search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
    search_results = collection.search(
        data=[query_embedding.tolist()],
        anns_field="embedding",
        param=search_params,
        limit=k,
        expr=None,
        output_fields=["path", "chunk_index", "content"]
    )
    return search_results[0]

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

def global_reorder_fixed_code(fixed_code: str) -> str:
    prompt = GLOBAL_REORDER_PROMPT.format(fixed_code=fixed_code)
    try:
        reordered_code = query_granite(prompt).strip()
        if reordered_code:
            print("[INFO] Successfully reordered variables globally.")
            return reordered_code
        else:
            print("[WARN] Empty reorder response, returning original fixed code.")
            return fixed_code
    except Exception as e:
        print(f"[ERROR] Global reorder failed: {e}")
        return fixed_code

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
            context_docs = get_top_k_chunks(embedding, k=5)
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

    merged_fixed_code = "\n\n".join(corrected_chunks)
    final_code = global_reorder_fixed_code(merged_fixed_code)

    print(f"\n[INFO] Granite full review + fix + global reorder took {time.time() - start_time:.2f} seconds.")

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


# --- Prompt templates ---

REVIEW_PROMPT_TEMPLATE = """You are an expert Terraform code reviewer focused on enforcing IBM Cloud standards for `variables.tf`.

Apply the following internal best practices:
{best_practices}

So far, the review has identified these issues:
{summary_section}

Analyze this Terraform code chunk and provide structured feedback. Strictly follow these rules while renaming and reviewing variables:

- Use `snake_case` for all variable names.
- Expand non-standard abbreviations (e.g., sm → secrets_manager).
- Preserve standard acronyms (`vpc`, `cos`, `kms`, `crn`).
- Boolean variables must begin with `enable_`, `disable_`, or `use_`.
- Suffix variable names with `_id`, `_name`, `_crn`, etc. where applicable.
- Prefix with `existing_` if referencing an existing resource.
- Group all `existing_*` variables before new ones.
- Review the `description` fields. If they are unclear, inaccurate, or incorrect, fix them.
- If a `description` is changed, add a comment line **above** the variable using the format: `# description updated`.
- Do NOT touch `validation` blocks.
- Do NOT explain anything — output only the corrected code, no extra text.

Terraform code chunk:
{chunk}
"""


FIX_PROMPT_TEMPLATE = """You are a Terraform expert improving a `variables.tf` chunk to meet IBM Cloud naming and documentation standards.

Strictly follow these rules:
- Use `snake_case` for all variable names.
- Expand non-standard abbreviations (e.g., sm → secrets_manager).
- Preserve standard acronyms (`vpc`, `cos`, `kms`, `crn`).
- Boolean variables must begin with `enable_`, `disable_`, or `use_`.
- Suffix variable names with `_id`, `_name`, `_crn`, etc. where applicable.
- Prefix with `existing_` if referencing an existing resource.
- Group all `existing_*` variables before new ones.
- Review the `description` fields. If they are unclear, inaccurate, or misleading, correct them.
- If you update a `description`, insert a comment above it: `# description updated`
- Do NOT modify `validation` blocks.
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
Summarize the main issues identified across all chunks (naming, grouping, structure).

Variable Rename Table (Markdown):
| Current Name | Suggested Name |
|--------------|----------------|
{rename_table}

Full Detailed Review:
{chunk_summaries}

Provide only the markdown content, no extra explanation or disclaimers.
"""

GLOBAL_REORDER_PROMPT = """You are an expert Terraform refactorer specializing in IBM Cloud best practices.

Given a complete `variables.tf` file, reorder and group all variables based on the following rules:

1. **Group variable definitions**: Ensure all input variables are defined in this file with consistent structure and clear descriptions.

2. **Prioritize and order variables for usability**:
   - Place frequently used, high-priority variables at the very top in the following order (if present): `region`, `prefix`, `resource_group_id`, `ibmcloud_api_key`.
   - These must appear at the top in the exact order above if they exist in the file.

3. **Co-locate related variables**:
   - Group variables by IBM Cloud service or domain such as `vpc`, `subnet`, `cluster`, `kms`, `code_engine`, `secrets_manager`, `logging`, etc.
   - Keep each group contiguous and logically ordered for readability and discoverability.

4. **Leverage sensible defaults**:
   - If a variable has a sensible default, preserve it.
   - Do not remove or alter existing defaults.
   - Review `description` fields and update them only if incorrect or unclear.
   - If a description is updated, insert a comment above it: `# description updated`
   - Do not add or remove variables.

5. **Do not modify validation blocks**:
   - Retain any `validation` blocks exactly as they are.

6. **Strict formatting rules**:
   - Use consistent spacing and indentation.
   - Preserve all existing `description` fields unless updated as above.
   - Output only the fully reordered `variables.tf` file — no explanations, no comments, no summaries.

Terraform file to reorder:
{fixed_code}
"""
