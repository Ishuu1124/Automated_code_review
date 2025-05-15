import os
import re
import time
import numpy as np
from dotenv import load_dotenv
from pymilvus import Collection, utility
from models.granite_model import query_granite, embed_text
from utils.chunker import chunk_text
from db.indexer import db

load_dotenv()

MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

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
            context_docs = db.get_top_k_chunks(embedding, 5)
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
            rename_table = "| Current Name | Suggested Name |\n|--------------|----------------|\n"
            for old, new in unique_renames:
                if old == new:
                    rename_table += f"| `{old}` | _No change_ |\n"
                else:
                    rename_table += f"| `{old}` | `{new}` |\n"
        else:
            rename_table = "_No renaming suggestions found._"

        final_prompt = FINAL_PROMPT_TEMPLATE.format(
            chunk_summaries=feedbacks,
            rename_table=rename_table
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

REVIEW_PROMPT_TEMPLATE = """You are an expert Terraform code reviewer focused on enforcing internal standards for `variables.tf` files used in IBM Cloud infrastructure.
Use the following best practices:
{best_practices}
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
- Use full words instead of abbreviations like `sm`, `kms`, `en`.
- Do NOT rename standard acronyms like `vpc` or `cos`.
- Boolean variables must begin with verbs (`use_`, `enable_`, `disable_`).
- Use suffixes like `_id`, `_name`, `_crn`.
- Prefix with `existing_` if variable refers to an existing resource.
- Maintain consistent prefixes for service-specific variables.
- Ensure all required variables appear before optional ones.
- Preserve all Terraform `validation` blocks exactly as they appear.
- Do not change or paraphrase the `description` field of any variable.
- Do not give explanations, only give corrected code.
- Do not give any text in between corrected code.

Context:
{context}

Code to fix:
{chunk}

Corrected Code:
"""

FINAL_PROMPT_TEMPLATE = """You are synthesizing a full review of a Terraform `variables.tf` file based on previous chunk-wise feedback and corrections.

You must generate the following output:

1. **Summary (2-3 sentences)**:
Briefly summarize the key naming and structure issues found across the file. Keep it concise and non-repetitive.

2. **Renamed Variables Table**:
Output a Markdown table mapping original variable names to their suggested renamed versions.
- Only include rows where the variable name has changed.
- Use this format:

| Current Variable Name              | Suggested Variable Name                                      |
|-----------------------------------|--------------------------------------------------------------|
| existingvpc                       | existing_vpc                                                 |
| sm_token                          | secrets_manager_token                                        |


---

Here is the input (chunk-level reviews and feedback):

{chunk_summaries}
Output:
"""



