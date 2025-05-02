import os
import time
import psycopg
import numpy as np
from dotenv import load_dotenv
from models.granite_model import query_granite, embed_text
from utils.chunker import chunk_text

load_dotenv()

FEW_SHOT_EXAMPLE = """
Example Issue:
Variable: `api_key`
Problem: Sensitive information not marked as `sensitive`.
Fix: Add `sensitive = true` to prevent exposure in logs.
Variable: `use_cos_for_backup`
Problem: Missing validation for boolean value.
Fix: Add a validation block ensuring it is either true or false.
Variable: `sm_token`
Problem: Acronym used; unclear to users unfamiliar with internal services.
Fix: Rename to `secrets_manager_token`.
Variable: `existingvpc`
Problem: Uses camelCase and lacks clarity about existing resources.
Fix: Rename to `existing_vpc` using snake_case and prefixing with `existing_`.
Variable: `disableFeature`
Problem: Boolean variable not starting with a verb.
Fix: Rename to `disable_feature_flag`.
Variable: `name_resource_group`
Problem: Incorrect order of terms.
Fix: Rename to `resource_group_name`.
"""

REVIEW_PROMPT_TEMPLATE = """You are an expert Terraform code reviewer focused on enforcing internal standards for `variables.tf` files used in IBM Cloud infrastructure.
Follow these conventions:
- Use full names for clarity. Avoid abbreviations like `sm`, `kms`, `en`. Instead use `secrets_manager`, `key_management_service`, `event_notification`, etc.
- However, you are allowed to use **industry-standard acronyms** like `vpc` (Virtual Private Cloud) and `cos` (Cloud Object Storage). Do NOT rename those.
- Use `snake_case` (underscores) instead of `camelCase`.
- Boolean variable names must begin with verbs like `use_`, `enable_`, or `disable_`. Avoid prefixes like `is_`.
- If a variable refers to an **existing resource**, prefix it with `existing_`.
- Suffix resource identifiers with `_id` or `_name`, not the other way around. E.g., `resource_group_id`, not `id_resource_group`.
- Prefix variables with service context if needed (e.g., `log_analysis_instance_name`).
- Group related variables with consistent prefixes.
- Group and name related variables consistently.
- Required variables (those without defaults) must be ordered at the top of the file, followed by optional ones.
- Preserve all Terraform `validation` blocks exactly as they appear in the input. Do not simplify, remove, or alter them, even if the values seem restrictive or verbose.
- Your task is to suggest improvements to variable names and structure *without modifying logic or validation rules*. Keep all existing constraints such as `validation` blocks, `default` values, and type definitions intact unless explicitly required to change.

Example Issues:
{few_shot_example}

So far, the review has identified these issues:
{summary_section}

Analyze the following chunk of Terraform code and provide:
- Variable names with issues
- Problem descriptions
- Suggested fixes (brief)
Respond in structured bullet points only.

Code to review:
{chunk}
"""

FIX_PROMPT_TEMPLATE = """You are a Terraform expert. Fix issues in this `variables.tf` chunk based on internal naming conventions.
Rules to follow:
- Rename variables to use `snake_case`.
- Use full words instead of abbreviations like `sm`, `kms`, `en`. Examples:
    - `apiKeySm` → `secrets_manager_api_key`
    - `kmsInstanceName` → `key_management_service_instance_name`
- Do NOT rename standard acronyms like `vpc` or `cos`.
- Boolean variables must begin with verbs (`use_`, `enable_`, `disable_`). Avoid `is_` and `has_`.
- Use suffixes like `_id`, `_name`, `_crn` at the end of variable names for clarity.
- Prefix with `existing_` if variable refers to an existing resource.
- Maintain contextual prefixes like `log_analysis_*`.
- Ensure all required variables (i.e., those without a `default`) appear before optional ones in the output.
- Maintain consistent and readable groupings for related variables.
- Preserve all Terraform `validation` blocks exactly as they appear in the input. Do not simplify, remove, or alter them, even if the values seem restrictive or verbose.
- Your task is to suggest improvements to variable names and structure *without modifying logic or validation rules*. Keep all existing constraints such as `validation` blocks, `default` values, and type definitions intact unless explicitly required to change.


Context:
{context}

Code to fix:
{chunk}

Corrected Code:"""

FINAL_PROMPT_TEMPLATE = """You are a Terraform expert reviewer.
You have reviewed several chunks of a `variables.tf` file and now need to generate a final, consolidated review.
Your goal is to:
- Summarize the key issues found across all chunks.
- Identify violations of naming conventions.
- Suggest consistent improvements.
Apply the following naming and structural standards:
- Use `snake_case`, not `camelCase`.
- Use full names in variable names instead of abbreviations (e.g., use `secrets_manager` not `sm`, `key_management_service` not `kms`, `event_notification` not `en`).
- However, preserve **industry-standard acronyms**, such as `vpc` (Virtual Private Cloud) and `cos` (Cloud Object Storage). Do NOT rename these.
- For booleans, use verb prefixes like `use_`, `enable_`, or `disable_`.
- Variables that reference existing resources must start with `existing_`.
- Use suffixes like `_id`, `_name`, or `_crn` consistently (e.g., `resource_group_id` not `id_resource_group`).
- When needed, use service-specific prefixes for context (e.g., `log_analysis_instance_name`).
- Group and order variables logically for usability and readability.
- Preserve all Terraform `validation` blocks exactly as they appear in the input. Do not simplify, remove, or alter them, even if the values seem restrictive or verbose.
- Your task is to suggest improvements to variable names and structure *without modifying logic or validation rules*. Keep all existing constraints such as `validation` blocks, `default` values, and type definitions intact unless explicitly required to change.


Input:
{chunk_summaries}

Your output must include:
1. **Final Consolidated Review**: A bullet-point summary of all issues found.
2. **Renamed Variables**: A mapping of problematic variable names → suggested names.
3. **Corrected variables.tf**: Show the fully corrected `variables.tf` content.
"""

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
    review_chunks = chunk_text(tf_text)
    print(f"[INFO] Total review chunks: {len(review_chunks)}")
    all_chunk_feedback = []
    corrected_chunks = []
    running_summary = []
    for i, chunk in enumerate(review_chunks):
        print(f"\n[INFO] Processing chunk {i + 1}/{len(review_chunks)}")
        try:
            embedding = np.array(embed_text(chunk))
            context_docs = get_top_k_chunks(embedding, k=5)
            context = "\n---\n".join([doc[2] for doc in context_docs])
            summary_section = "\n".join(running_summary[-5:]) or "No issues found yet."
            review_prompt = REVIEW_PROMPT_TEMPLATE.format(
                few_shot_example=FEW_SHOT_EXAMPLE,
                summary_section=summary_section,
                chunk=chunk
            )
            review_response = query_granite(review_prompt).strip()
            if not review_response or review_response.startswith("[Error"):
                print(f"[ERROR] No review response for chunk {i}. Review response: {review_response}")
            else:
                print(f"[INFO] Review response for chunk {i}: {review_response}")
            all_chunk_feedback.append((i, review_response))
            running_summary.append(review_response)
        except Exception as e:
            print(f"[ERROR] Failed review for chunk {i}: {e}")
            all_chunk_feedback.append((i, "[ERROR] Review failed"))
            continue
        try:
            fix_prompt = FIX_PROMPT_TEMPLATE.format(
                context=context,
                chunk=chunk
            )
            fix_response = query_granite(fix_prompt).strip()
            corrected_chunks.append(fix_response)
        except Exception as e:
            print(f"[ERROR] Failed fix for chunk {i}: {e}")
            corrected_chunks.append(chunk)
    feedbacks = "\n\n".join([f"Chunk {i}:\n{resp}" for i, resp in all_chunk_feedback])
    print(f"\n[INFO] Feedbacks collected: {feedbacks}")
    try:
        final_prompt = FINAL_PROMPT_TEMPLATE.format(chunk_summaries=feedbacks)
        final_review = query_granite(final_prompt).strip()
        print(f"[INFO] Final review response: {final_review}")
    except Exception as e:
        print(f"[ERROR] Final review synthesis failed: {e}")
        final_review = "[ERROR] Could not generate consolidated review."
    final_code = "\n\n".join(corrected_chunks)
    print(f"\n[INFO] Granite full review + fix took {time.time() - start_time:.2f} seconds.")
    return {
        "final_review": final_review,
        "corrected_code": final_code
    }