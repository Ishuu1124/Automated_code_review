# 🛠 IBM Cloud Terraform Variable Reviewer

A GitHub-integrated review bot that automatically evaluates `variables.tf` files against best practices, suggests improvements, and generates corrected Terraform code using RAG (Retrieval-Augmented Generation) powered by the Granite LLM and Milvus.



## 🚀 Features

* Automatically reviews `variables.tf` files in PRs or local code.
* Checks for naming convention violations and structural issues.
* Uses best practices and context-aware retrieval.
* Preserves descriptions and validation blocks during fixes.
* Outputs clean reviews, renamed variable mapping, and corrected code.



## 📦 Folder Structure

```bash
.
├── db/
│   └── indexer.py               # Embeds and indexes best practices in Milvus
├── retriever/
│   └── simple_rag.py            # RAG pipeline for review and fix
├── evaluator/
│   └── scorer.py                # Basic evaluation scoring utilities
├── utils/
│   └── chunker.py               # Text chunking logic
├── models/
│   └── granite_model.py         # Granite model wrapper (via Ollama)
├── guide/
│   └── bp.txt       # Best practices for Terraform variable files
├── ghub.py                      # GitHub integration to review remote PRs
├── ghub_utils.py
├── .env                         # Environment variables
├── milvus-standalone/
│   └── docker-compose.yml       # Milvus standalone setup
```



## ✅ Prerequisites

* Python 3.8+
* Docker & Docker Compose
* [Ollama](https://ollama.com) installed with `granite3.3`



## 🔧 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Ishuu1124/Automated_code_review.git
cd Automated_code_review
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the root directory:

```env
MILVUS_HOST=localhost
MILVUS_PORT=19530
COLLECTION_NAME=docs
GUIDE_FOLDER_PATH=guide
GITHUB_BOT_SECRET=
GITHUB_BOT_ID=
REDIS_URL=
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
```

### 4. Start Milvus Locally

```bash
docker-compose up -d
```

Wait until Milvus is up (check logs with `docker-compose logs -f`).

### 5. Start Ollama with Granite

```bash
ollama run granite3.3
```

## 🔍 Usage


### Start script

```
./start_celery.sh
```


This fetches `variables.tf` from the root of the given repo, runs a review, and prints:

* ✅ Review Summary
* 📝 Suggested Renames
* 🔧 Corrected Code
* 📊 Score & Token Count



## 📁 Guide Files

Put all `.txt` documents outlining variable naming conventions, structuring rules, etc., in the `guide/` folder. These serve as context for the review.


## 🧠 Behind the Scenes

* ✅ Embeddings: `all-MiniLM-L6-v2` via `sentence-transformers`
* 🔍 Vector DB: Milvus standalone (Docker)
* 🧠 LLM: Granite Code (via Ollama)
* 📎 RAG: Context retrieved from `guide/*.txt`
* 🛠 Fixes: LLM rewrites chunks while preserving validation and descriptions



## 🛑 Notes

* Only the `variables.tf` file is currently reviewed.
* Descriptions and validation blocks are never altered.
* No extra explanations are included in the final fixed code.