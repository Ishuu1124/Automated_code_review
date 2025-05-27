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
    """
    Call Granite LLM to reorder and group related variables globally after chunk fixes.
    """
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

    # Merge all fixed chunks into one string
    merged_fixed_code = "\n\n".join(corrected_chunks)

    # NEW: Run global reorder step on the merged fixed code
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

REVIEW_PROMPT_TEMPLATE = """You are an expert Terraform reviewer enforcing IBM Cloud standards for `variables.tf` files.

Apply the following internal best practices:
{best_practices}

The review so far has identified:
{summary_section}

Analyze the following Terraform code chunk and provide bullet-point feedback. Strictly follow these rules when identifying issues or renaming variables:
- Use `snake_case` for all variable names.
- Expand non-standard abbreviations (e.g., `sm` → `secrets_manager`).
- Preserve standard acronyms (`vpc`, `cos`, `kms`, `crn`).
- Boolean variable names must start with `enable_`, `disable_`, or `use_`.
- Use suffixes like `_id`, `_name`, `_crn` where appropriate.
- Prefix with `existing_` if referencing existing resources.
- Group all `existing_*` variables before new ones.
- Do **not** modify `validation` blocks.
- Only change `description` if it is inaccurate — append `#description updated`.
- If `description` is missing, add a meaningful one — append `#description added`.
- Do not explain — output bullet points only, no extra text.

Terraform code chunk:
{chunk}
"""

FIX_PROMPT_TEMPLATE = """You are a Terraform expert improving a `variables.tf` chunk to comply with IBM Cloud naming and structure standards.

Follow these rules exactly:
- Use `snake_case` for all variable names.
- Expand non-standard abbreviations (e.g., `sm` → `secrets_manager`).
- Preserve standard acronyms (`vpc`, `cos`, `kms`, `crn`).
- Boolean variable names must start with `enable_`, `disable_`, or `use_`.
- Use suffixes like `_id`, `_name`, `_crn` where appropriate.
- Prefix with `existing_` if referencing existing resources.
- Group all `existing_*` variables before new ones.
- Do **not** touch `validation` blocks.
- Only update `description` if incorrect — append `#description updated`.
- Add missing `description` fields — append `#description added`.
- Do not explain — output only the corrected code, no extra text.

Context:
{context}

Terraform code chunk:
{chunk}

Corrected code:
"""

FINAL_PROMPT_TEMPLATE = """You are generating a final Terraform `variables.tf` review by synthesizing chunk-level feedback and fixes.

Output the following in markdown format only:

### **Summary**
(2–3 sentences summarizing major issues such as naming inconsistencies, grouping gaps, or structural problems.)

### **Variable Rename Table**
| Current Name | Suggested Name |
|--------------|----------------|
{rename_table}

### **Detailed Review**
{chunk_summaries}

Do not include explanations or commentary outside the markdown.
"""

GLOBAL_REORDER_PROMPT = """You are a Terraform expert refactoring a complete `variables.tf` file according to IBM Cloud best practices.

Reorder and group variables following these rules:

1. **Group definitions**: Ensure all input variables are present, consistently structured, and include accurate descriptions.
2. **Domain grouping**: Cluster related variables by domain (e.g., VPC, Cluster, Key Management, Logging, Secrets Manager).
3. **Usability ordering**:
   - Place variables without default values at the top.
   - Then list high-priority variables like `region`, `prefix`, `ibm_cloud_api_key`.
   - Follow with logically grouped domain blocks.
4. **Preserve defaults**: Retain all existing sensible defaults.
5. **Do not alter validation**: Preserve all `validation` and nested `policy` blocks exactly as-is.
6. **Strict formatting**:
   - Use consistent spacing and indentation.
   - Do not change correct descriptions.
7. **Do not add/remove any variables**.

Input:
{fixed_code}

Output the fully reordered `variables.tf` file — no extra text or comments.
"""