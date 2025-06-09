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
        if not utility.has_collection(COLLECTION_NAME):
            print(f"[ERROR] Collection {COLLECTION_NAME} not found in Milvus!")
            return None
        print(f"[INFO] Found collection {COLLECTION_NAME}")
        collection = Collection(COLLECTION_NAME)
        return collection
    except Exception as e:
        print(f"[ERROR] Failed to load collection from Milvus: {e}")
        return None


def get_top_k_chunks(query_embedding, k=5):
    collection = get_milvus_connection()
    if not collection:
        return []
    collection.load()
    search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
    search_results = collection.search(
        data=[query_embedding.tolist()],
        anns_field="embedding",
        param=search_params,
        limit=k,
        expr=None,
        output_fields=["path", "chunk_index", "content"],
    )
    return search_results[0]


def extract_renamed_vars_with_reasons(review_text: str) -> list[tuple[str, str, str]]:
    pattern = r"`?(\w+)`?\s*->\s*`?(\w+)`?(?:\s*:\s*(.*))?"
    return re.findall(pattern, review_text)


def extract_validation_blocks(text: str) -> dict:
    variable_blocks = re.findall(
        r'(variable\s+"[^"]+"\s*{[^}]*?(validation\s*{[^}]*}[^}]*?)+})', text, re.DOTALL
    )
    return {
        re.search(r'variable\s+"([^"]+)"', block[0]).group(1): block[0]
        for block in variable_blocks
        if re.search(r'variable\s+"([^"]+)"', block[0])
    }


def reinsert_validation_blocks(original: str, fixed: str) -> str:
    original_blocks = extract_validation_blocks(original)
    for var_name, original_block in original_blocks.items():
        fixed = re.sub(
            rf'(variable\s+"{re.escape(var_name)}"\s*{{)(.*?)(}})',
            lambda m: original_block,
            fixed,
            flags=re.DOTALL,
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
    renamed_variables_with_lines = []
    best_practices = load_best_practices()

    for i, chunk_info in enumerate(review_chunks):
        chunk_text_str = chunk_info["chunk"]
        start_line = chunk_info.get("start_line", -1)
        var_line_map = chunk_info.get("var_line_map", {})

        print(
            f"\n[INFO] Processing chunk {i + 1}/{len(review_chunks)} (starting at line {start_line})"
        )
        try:
            embedding = np.array(embed_text(chunk_text_str))
            context_docs = get_top_k_chunks(embedding, k=5)
            context = "\n---\n".join([doc[2] for doc in context_docs])
            summary_section = "\n".join(running_summary[-5:]) or "No issues found yet."

            review_prompt = REVIEW_PROMPT_TEMPLATE.format(
                best_practices=best_practices,
                summary_section=summary_section,
                chunk=chunk_text_str,
            )
            review_response = query_granite(review_prompt).strip()
            if review_response and not review_response.startswith("[Error"):
                print(f"[INFO] Review response for chunk {i+1}:\n{review_response}")
                for old, new, reason in extract_renamed_vars_with_reasons(
                    review_response
                ):
                    # Get the actual line number of the variable inside the chunk if possible
                    actual_line = var_line_map.get(old, start_line)
                    renamed_variables_with_lines.append((old, new, reason, actual_line))
            else:
                print(f"[ERROR] No valid review response for chunk {i+1}")
            all_chunk_feedback.append((i + 1, review_response))
            running_summary.append(review_response)
        except Exception as e:
            print(f"[ERROR] Review failed for chunk {i+1}: {e}")
            all_chunk_feedback.append((i + 1, "[ERROR] Review failed"))
            continue

        try:
            fix_prompt = FIX_PROMPT_TEMPLATE.format(
                context=context, chunk=chunk_text_str
            )
            fix_response = query_granite(fix_prompt).strip()
            fixed_with_validation = reinsert_validation_blocks(
                chunk_text_str, fix_response
            )
            corrected_chunks.append(fixed_with_validation)
        except Exception as e:
            print(f"[ERROR] Fix failed for chunk {i+1}: {e}")
            corrected_chunks.append(chunk_text_str)

    feedbacks = "\n\n".join([f"Chunk {i}:\n{resp}" for i, resp in all_chunk_feedback])

    try:
        if renamed_variables_with_lines:
            # Sort and deduplicate
            seen = set()
            unique_renames = []
            for old, new, reason, line in renamed_variables_with_lines:
                key = (old, new)
                if old != new and key not in seen:
                    unique_renames.append((old, new, reason, line))
                    seen.add(key)

            rename_table_rows = "\n".join(
                f"| `{old}` | `{new}` | {reason.strip() if reason else '_No reason provided_'} | {line} |"
                for old, new, reason, line in unique_renames
            )
        else:
            rename_table_rows = "_No renaming suggestions found._"

        final_prompt = FINAL_PROMPT_TEMPLATE.format(
            chunk_summaries=feedbacks, rename_table=rename_table_rows
        )
        final_review = query_granite(final_prompt).strip()
        print("[INFO] Final review generated.")
    except Exception as e:
        print(f"[ERROR] Final review synthesis failed: {e}")
        final_review = "[ERROR] Could not generate consolidated review."

    merged_fixed_code = "\n\n".join(corrected_chunks)
    final_code = global_reorder_fixed_code(merged_fixed_code)

    print(f"\n[INFO] Total RAG review time: {time.time() - start_time:.2f} seconds.")

    return {"final_review": final_review, "corrected_code": final_code}


def load_best_practices() -> str:
    best_practices = ""
    guide_folder = os.getenv("GUIDE_FOLDER_PATH")
    if not guide_folder or not os.path.isdir(guide_folder):
        print("[ERROR] GUIDE_FOLDER_PATH is not set or invalid.")
        return best_practices

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
- Preserve standard acronyms (`vpc`, `cos`, `kms`, `crn`, `ocp`, `vpe`).
- Boolean variable names must start with `enable_`, `disable_`, or `use_`.
- Use suffixes like `_id`, `_name`, `_crn` where appropriate.
- Prefix with `existing_` if referencing existing resources.
- Group all `existing_*` variables before new ones.
- Do **not** modify `validation` blocks.
- Only update the `description` field if incorrect — in that case, add a new comment line directly **above** the `description` line containing `#description updated`.
- If the `description` is missing, add a meaningful one, and **add a comment line immediately below**: `#description added`.
- Do not explain — output bullet points only, no extra text.
- Do not suggest renaming the same variable more than once across chunks.

For variable renaming suggestions, use this format:
`old_name` -> `new_name`: Provide a short, clear reason. Do **not** start the reason with "reason:".

Terraform code chunk:
{chunk}
"""

FIX_PROMPT_TEMPLATE = """You are a Terraform expert improving a `variables.tf` chunk to comply with IBM Cloud naming and structure standards.

Follow these rules exactly:
- Use `snake_case` for all variable names.
- Expand non-standard abbreviations (e.g., `sm` → `secrets_manager`).
- Preserve standard acronyms (`vpc`, `cos`, `kms`, `crn`, `ocp`, `vpe`).
- Boolean variable names must start with `enable_`, `disable_`, or `use_`.
- Use suffixes like `_id`, `_name`, `_crn` where appropriate.
- Prefix with `existing_` if referencing existing resources.
- Group all `existing_*` variables before new ones.
- Do **not** touch `validation` blocks.
- Only update the `description` field if it is incorrect or missing.
- If the `description` is incorrect, keep the updated `description` field, and **add a new line directly above it with** `#description updated` as a comment — **do not include this tag inside the description string**.
- If the `description` is missing, add a meaningful one, and **add a comment line immediately below**: `#description added`.
- Do not repeat or duplicate variable definitions across the file.
- Do not rename a variable if it has already been renamed in a previous chunk.
- Output only the corrected Terraform code — no extra text.

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
| Current Name | Suggested Name | Reason for the suggested change | Line Number |
|--------------|----------------|----------------------------------|-------------|
{rename_table}

### **Detailed Review**
{chunk_summaries}

Do not include explanations or commentary outside the markdown.
Ensure the rename table reflects only actual changes made and is deduplicated.
Ensure the "Reason for the suggested change" is clear and concise. Do **not** start reasons with “reason:”.
"""

GLOBAL_REORDER_PROMPT = """You are a Terraform expert refactoring a complete `variables.tf` file according to IBM Cloud best practices.

Reorder and group variables following these exact rules:

1. **Deduplicate**:
   - Do not allow the same logical input to be defined multiple times with different names (e.g., `existing_api_key` and `ibmcloud_api_key`).
   - Keep only one canonical version of any overlapping or renamed variable.
   - Prefer IBM Cloud standard names such as `ibmcloud_api_key`, `region`, and `prefix` where applicable.

2. **Ordering by Defaults**:
   - Place all variables that do **not** have `default =` at the **top** of the file.
   - Then place variables **with defaults** afterward.

3. **Domain Grouping**:
   - Cluster variables into logical blocks by their usage (e.g., Secrets Manager, VPC, Resource Group, Tags, Logging).
   - Group all `existing_*` variables before new ones in their domain.

4. **High-priority input variables**:
   - Within the "no default" block, order as follows: `ibmcloud_api_key`, `region`, `prefix`.

5. **Preserve values**:
   - Keep all default values as-is.
   - Do not alter validation or policy blocks.

6. **Formatting**:
   - Use consistent indentation.
   - Ensure every variable block is complete and syntactically valid.
   - Remove any duplicated or conflicting definitions.

Your output must include only valid, clean, deduplicated, and fully reordered Terraform code. Do not add, repeat, or keep multiple definitions for the same logical variable.
Input:
{fixed_code}

Output:
"""
