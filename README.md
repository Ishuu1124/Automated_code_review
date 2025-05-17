# 🧠 Terraform RAG Review Bot with Granite 3.3

A GitHub-integrated **RAG-based reviewer** that automatically analyzes `variables.tf` files for naming and structure violations, suggests fixes, and generates corrected Terraform code using **Granite 3.3** (via **Ollama**) and **Milvus** or **pgVector** for context retrieval.

![Architecture Diagram](https://github.com/user-attachments/assets/1e2b333b-7571-4247-8d61-dad197c6a309)


## 🚀 Features

* ✅ Automated review of `variables.tf` files from PRs or local code.
* 🤖 Uses Retrieval-Augmented Generation with Granite 3.3 LLM.
* 📎 Embeds and retrieves Terraform best practices from `.txt` and `.tf` files.
* 🧠 Fixes issues while preserving validation and description blocks.
* 📋 Outputs clean review summary, rename suggestions, corrected code, and scoring.



## 📁 Folder Structure

```bash
.
├── db/
│   ├── pgvector_conn.py         # PgVector connection setup (if using PostgreSQL)
│   └── indexer.py               # Embeds and indexes best practices in Milvus/pgVector
├── retriever/
│   └── simple_rag.py            # RAG pipeline for review and fix
├── evaluator/
│   └── scorer.py                # Evaluation scoring utilities
├── utils/
│   └── chunker.py               # Text chunking logic
├── models/
│   └── granite_model.py         # Granite model wrapper (via Ollama)
├── guide/
│   └── bp.txt                   # Best practices for Terraform variable files
├── ghub.py                      # GitHub PR integration
├── ghub_utils.py                # GitHub utility functions
├── milvus-standalone/
│   └── docker-compose.yml       # Milvus setup (if using Milvus)
├── .env                         # Environment variables
```



## ✅ Prerequisites

* Python 3.8+
* [Ollama](https://ollama.com) with `granite3.3` pulled
* A running instance of [webhook receiver](https://github.com/aamadeuss/webhook-receiver/tree/tf-review?tab=readme-ov-file#webhook-receiver)
 * Note the Redis URL used for the webhook receiver; it has to be reused here.
* Either:

  * **PostgreSQL** with `pgvector` extension enabled, or
  * **Milvus** (via Docker) for vector storage

* A GitHub bot set up as follows:

  - With permissions to read and write repository contents and comments on pull requests and issues:
  
  ![image](https://github.com/user-attachments/assets/92f4472b-08e4-4cc2-9bca-002d49dbec93)


  ![image](https://github.com/user-attachments/assets/2149b3ad-792f-433c-9f41-7df6e330c3b0)

  
  ![image](https://github.com/user-attachments/assets/9357f981-02f7-4fda-99aa-e89a68b992b9)


   - Subscribed to events for comments created in issues and pull requests:

  ![image](https://github.com/user-attachments/assets/48f4a917-f287-4941-a770-05d58e68ec92)


  - Install the GitHub bot to the required repository.


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

### 3. Configure `.env` File

For **Milvus**:

```env
MILVUS_HOST=localhost
MILVUS_PORT=19530
COLLECTION_NAME=docs
```

For **pgVector**:

```env
DB_NAME=rag_db
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

Common settings for both db options:

```env
GUIDE_FOLDER_PATH=guide
GITHUB_BOT_SECRET=
GITHUB_BOT_ID=
REDIS_URL=
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
```
*`REDIS_URL`, `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` have to be the same Redis URL as the webhook receiver.*

### 4. Start Vector DB

* For **Milvus**:

  ```bash
  cd milvus-standalone/milvus-docker
  podman-compose up -d
  ```

  *(Check logs with `docker-compose logs -f`)*

* For **pgVector**:

  In a separate terminal, run:

  ```bash
  psql -U <your-username> -d <db_name>
  ```
  The username and db_name should be the same given in `.env`.

  In the db terminal, run:

  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```

### 5. Pull model from Ollama

```bash
ollama pull granite3.3
```



## 🔍 Usage

To run the reviewer:

```bash
./start_celery.sh
```

The process can be initiated using the command `/tf_review` in a PR with the GitHub bot installed in the repo.

This will:

* Fetch `variables.tf` from a PR or local repo root
* Run a context-aware review
* Print:

  * ✅ Review Summary
  * 📝 Suggested Renames
  * 🔧 Corrected Code
  * 📊 Score & Token Count


## 📚 Guide Files

Add your `.txt` and `.tf` best practice documents to the `guide/` folder. These are indexed for retrieval and used during code evaluation.



## 🧠 Behind the scenes

* Embedding Model: `all-MiniLM-L6-v2` via `sentence-transformers`
* Vector DB: Milvus (Docker) or pgVector (PostgreSQL)
* LLM: Granite 3.3 via Ollama
* RAG: Chunks retrieved from `guide/*.txt`
* Fix Logic: Chunk rewriting with preservation of validation and descriptions


## 🛑 Notes

* Only `variables.tf` is currently supported.
* Descriptions and validation blocks are never modified.
* Final code output contains **no extra explanations**—just clean, fixed Terraform code.


