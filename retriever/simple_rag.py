import os
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

def run_simple_rag(tf_text: str) -> dict:
    start_time = time.time()
    review_chunks = chunk_text(tf_text, file_type="tf")
    print(f"[INFO] Total review chunks: {len(review_chunks)}")
    all_chunk_feedback = []
    corrected_chunks = []
    running_summary = []

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
            if not review_response or review_response.startswith("[Error"):
                print(f"[ERROR] No review response for chunk {i+1}. Review response: {review_response}")
            else:
                print(f"[INFO] Review response for chunk {i+1}: {review_response}")
            all_chunk_feedback.append((i+1, review_response))
            running_summary.append(review_response)
        except Exception as e:
            print(f"[ERROR] Failed review for chunk {i+1}: {e}")
            all_chunk_feedback.append((i+1, "[ERROR] Review failed"))
            continue

        try:
            fix_prompt = FIX_PROMPT_TEMPLATE.format(
                context=context,
                chunk=chunk
            )
            fix_response = query_granite(fix_prompt).strip()
            corrected_chunks.append(fix_response)
        except Exception as e:
            print(f"[ERROR] Failed fix for chunk {i+1}: {e}")
            corrected_chunks.append(chunk)

    feedbacks = "\n\n".join([f"Chunk {i+1}:\n{resp}" for i, resp in all_chunk_feedback])
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

Context:
{context}

Code to fix:
{chunk}

Corrected Code:
"""

FINAL_PROMPT_TEMPLATE = """You are a Terraform expert reviewer.
You have reviewed several chunks of a `variables.tf` file and now need to generate a final, consolidated review.
Summarize the key issues found across all chunks and suggest consistent improvements.

Follow these conventions:
- Use `snake_case` for variable names.
- Use full names for variables (e.g., `secrets_manager` instead of `sm`).
- Preserve industry-standard acronyms (e.g., `vpc`, `cos`).
- Boolean variables should start with verbs like `use_`, `enable_`, or `disable_`.
- Variables referring to existing resources must start with `existing_`.
- Use suffixes like `_id`, `_name`, or `_crn`.
- Maintain consistent prefixes for related variables.
- Preserve all Terraform `validation` blocks exactly as they appear.

Input:
{chunk_summaries}

Your output must include:
1. **Final Consolidated Review**: A bullet-point summary of all issues found.
2. **Renamed Variables**: A mapping of problematic variable names → suggested names.
3. **Corrected variables.tf**: Show the fully corrected `variables.tf` content.
"""
