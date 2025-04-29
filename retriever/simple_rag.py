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
Your review must check for the following:
- Use full names, avoid acronyms unless industry-standard (e.g., `vpc`, `cos`)
- Use `snake_case`, not `camelCase`
- Variable naming must end with `id`, `name`, etc. (e.g., `resource_group_id`)
- Boolean variable names must start with verbs (e.g., `use_private_endpoint`)
- Variables referring to pre-existing infrastructure must start with `existing_`
- Contextual prefixes for services (e.g., `log_analysis_secret_name`) when module handles multiple services
- Related variables should be grouped logically
- Frequently used variables (e.g., `resource_group`, `region`) should appear near the top
- Provide sensible defaults wherever appropriate
- Avoid unnecessary changes. Only suggest changes if there is a clear violation.

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

FIX_PROMPT_TEMPLATE = """You are a Terraform expert. Fix issues in this `variables.tf` chunk:
- Use full names, avoid acronyms unless standard (e.g., use `secrets_manager` instead of `sm`)
- Use `snake_case` and order suffixes properly (`*_id`, `*_name`)
- Boolean variable names must start with a verb
- Prefix with `existing_` for pre-existing resources
- Maintain context-appropriate service prefixes
- Add sensible defaults unless absolutely required
- Preserve description text
- Output *only* the corrected Terraform code — no explanations or comments.

Context:
{context}

Code to fix:
{chunk}

Corrected Code:"""

FINAL_PROMPT_TEMPLATE = """You are an expert Terraform reviewer for IBM Cloud. Below is feedback from individual chunks of a `variables.tf` file.
Your task is to synthesize a *final consolidated review*:
- Focus only on `variable` definitions.
- Merge similar issues and remove duplicates.
- DO NOT introduce content that was not in the input code.
- Highlight patterns and group findings logically (e.g., naming, validation, sensitive data).
- Avoid summarizing Terraform best practices unrelated to the actual variables.

Chunk feedback:
{feedbacks}

Final Review:"""

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
        final_prompt = FINAL_PROMPT_TEMPLATE.format(feedbacks=feedbacks)
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

# import os
# import time
# import psycopg
# import numpy as np  
# from dotenv import load_dotenv
# from models.granite_model import query_granite, embed_text
# from utils.chunker import chunk_text

# load_dotenv()

# FEW_SHOT_EXAMPLE = """
# Example Issue:
# Variable: `api_key`
# Problem: Sensitive information not marked as `sensitive`.
# Fix: Add `sensitive = true` to prevent exposure in logs.
# Variable: `use_cos_for_backup`
# Problem: Missing validation for boolean value.
# Fix: Add a validation block ensuring it is either true or false.
# """

# REVIEW_PROMPT_TEMPLATE = """You are an expert Terraform code reviewer focused on enforcing internal standards for `variables.tf` files used in IBM Cloud infrastructure.

# Example Issues:
# {few_shot_example}

# So far, the review has identified these issues:
# {summary_section}

# Analyze the following chunk of Terraform code and provide:
# - Variable names with issues
# - Problem descriptions
# - Suggested fixes (brief)
# Respond in structured bullet points only.

# Code to review:
# {chunk}
# """

# FIX_PROMPT_TEMPLATE = """You are a Terraform expert. Fix issues in this `variables.tf` chunk:
# - Sensitive variables must have `sensitive = true`
# - Required variables should be ordered first
# - Validate enums and boolean types with `validation` blocks
# - Do not modify descriptions
# - Output only the corrected Terraform code — no explanations or comments.

# Context:
# {context}

# Code to fix:
# {chunk}

# Corrected Code:"""
# FINAL_PROMPT_TEMPLATE = """You are an expert Terraform reviewer for IBM Cloud. Below is feedback from individual chunks of a `variables.tf` file.
# Your task is to synthesize a *final consolidated review*:
# - Focus only on `variable` definitions.
# - Merge similar issues and remove duplicates.
# - DO NOT introduce content that was not in the input code.
# - Highlight patterns and group findings logically (e.g., naming, validation, sensitive data).
# - Avoid summarizing Terraform best practices unrelated to the actual variables.

# Chunk feedback:
# {feedbacks}

# Final Review:"""

# def get_pgvector_connection():
#     return psycopg.connect(
#         dbname=os.getenv("DB_NAME"),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         host=os.getenv("DB_HOST"),
#         port=os.getenv("DB_PORT")
#     )

# def get_top_k_chunks(query_embedding, k=20, filter_by_filename="variables.tf"):
#     conn = get_pgvector_connection()
#     with conn.cursor() as cur:
#         sql = """
#             SELECT path, chunk_index, content, content_hash, embedding
#             FROM docs
#         """
#         if filter_by_filename:
#             sql += f" WHERE path LIKE '%%{filter_by_filename}'"
#         sql += " ORDER BY embedding <-> %s::vector LIMIT %s"
#         cur.execute(sql, (query_embedding.tolist(), k))
#         context_chunks = cur.fetchall()
#     conn.close()
#     return context_chunks

# def run_simple_rag(tf_text: str) -> dict:
#     start_time = time.time()
#     review_chunks = chunk_text(tf_text)
#     print(f"[INFO] Total review chunks: {len(review_chunks)}")
#     all_chunk_feedback = []
#     corrected_chunks = []
#     running_summary = []
#     for i, chunk in enumerate(review_chunks):
#         print(f"\n[INFO] Processing chunk {i + 1}/{len(review_chunks)}")
#         try:
#             embedding = np.array(embed_text(chunk))  
#             context_docs = get_top_k_chunks(embedding, k=5)
#             context = "\n---\n".join([doc[2] for doc in context_docs])
#             summary_section = "\n".join(running_summary[-5:]) or "No issues found yet."
#             review_prompt = REVIEW_PROMPT_TEMPLATE.format(
#                 few_shot_example=FEW_SHOT_EXAMPLE,
#                 summary_section=summary_section,
#                 chunk=chunk
#             )
#             review_response = query_granite(review_prompt).strip()
#             if not review_response or review_response.startswith("[Error"):
#                 print(f"[ERROR] No review response for chunk {i}. Review response: {review_response}")
#             else:
#                 print(f"[INFO] Review response for chunk {i}: {review_response}")
#             all_chunk_feedback.append((i, review_response))
#             running_summary.append(review_response)
#         except Exception as e:
#             print(f"[ERROR] Failed review for chunk {i}: {e}")
#             all_chunk_feedback.append((i, "[ERROR] Review failed"))
#             continue
#         try:
#             fix_prompt = FIX_PROMPT_TEMPLATE.format(
#                 context=context,
#                 chunk=chunk
#             )
#             fix_response = query_granite(fix_prompt).strip()
#             corrected_chunks.append(fix_response)
#         except Exception as e:
#             print(f"[ERROR] Failed fix for chunk {i}: {e}")
#             corrected_chunks.append(chunk)
#     feedbacks = "\n\n".join([f"Chunk {i}:\n{resp}" for i, resp in all_chunk_feedback])
#     print(f"\n[INFO] Feedbacks collected: {feedbacks}")
#     try:
#         final_prompt = FINAL_PROMPT_TEMPLATE.format(feedbacks=feedbacks)
#         final_review = query_granite(final_prompt).strip()
#         print(f"[INFO] Final review response: {final_review}")
#     except Exception as e:
#         print(f"[ERROR] Final review synthesis failed: {e}")
#         final_review = "[ERROR] Could not generate consolidated review."
#     final_code = "\n\n".join(corrected_chunks)
#     print(f"\n[INFO] Granite full review + fix took {time.time() - start_time:.2f} seconds.")
#     return {
#         "final_review": final_review,
#         "corrected_code": final_code
#     }