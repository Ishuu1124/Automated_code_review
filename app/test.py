from app.models.granite_model import query_watsonx, embed_watson
code = """
variable "ibmcloud_api_key" {
  type        = string
  description = "The IBM Cloud API Key."
  sensitive   = true
}

variable "region" {
  type        = string
  description = "Region to provision all resources created by this example."
}

variable "prefix" {
  type        = string
  description = "A string value to prefix to all resources created by this example."
}

variable "resource_group" {
  type        = string
  description = "The name of an existing resource group to provision resources in to. If not set a new resource group will be created using the prefix variable."
  default     = null
}

variable "resource_tags" {
  type        = list(string)
  description = "List of resource tag to associate with all resource instances created by this example."
  default     = []
}

variable "access_tags" {
  type        = list(string)
  description = "Optional list of access management tags to add to resources that are created."
  default     = []
}"
"""
response = query_watsonx("hi")
print(response)

import os
import time
import glob
import hashlib
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from pymilvus import Collection, connections
from app.utils.chunker import chunk_text
from app.db.dbFactory import dbFactory


load_dotenv()
DATA_DIR = "app/guide"
# model = SentenceTransformer("all-MiniLM-L6-v2")


db = dbFactory.makedb("postgres")

def index_docs(folder=DATA_DIR):
    start_time = time.time()

    files = glob.glob(os.path.join(folder, "*.txt")) + glob.glob(os.path.join(folder, "*.tf"))
    total_files = len(files)
    updated_chunks = 0

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        ext = os.path.splitext(path)[1].lower()
        file_type = "tf" if ext == ".tf" else "txt"
        chunks = chunk_text(content, file_type=file_type)

        # embeddings = model.encode(chunks, batch_size=32, show_progress_bar=True)
        embeddings = embed_watson(chunks)
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            content_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
            db.add_index(path, i, chunk, content_hash, embedding)
            updated_chunks+=1
    
    db.close_conn()

    duration = time.time() - start_time
    print(f"[INFO] Indexed {total_files} files with {updated_chunks} updated chunks in {duration:.2f} seconds.")
