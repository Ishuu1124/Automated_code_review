# Terraform RAG Evaluation with Granite 3.3
- This project compares Terraform code files (`variables.tf`) against best practices using **Simple RAG (Retrieval-Augmented Generation)** powered by **Granite 3.3** LLM (via Ollama). The system retrieves reference context from ingested `.txt` and `.tf` documents, and evaluates target Terraform files for potential improvements.
- Arcihtecture Diagram:


![image](https://github.com/user-attachments/assets/1e2b333b-7571-4247-8d61-dad197c6a309)

---
## Features
- **Granite 3.3** LLM integration via Ollama.
- Ingests Terraform best practices and examples from `.txt` and `.tf` files.
- Embeds documents using `sentence-transformers` and stores them in **pgVector (PostgreSQL)**.
- Retrieves top relevant context to construct prompts for code evaluation.


## 📦 Folder Structure

```bash
.
├── db/
│   └── pgvector_conn.py         # PgVector connection setup
│   └── indexer.py               # Embeds and indexes best practices in PgVector
├── retriever/
│   └── simple_rag.py            # RAG pipeline for review and fix
├── evaluator/
│   └── scorer.py                # Basic evaluation scoring utilities
├── utils/
│   └── chunker.py               # Text chunking logic
├── models/
│   └── granite_model.py         # Granite model wrapper (via Ollama)
├── guide/
│   └── bp.txt                   # Best practices for Terraform variable files
├── ghub.py                      # GitHub integration to review remote PRs
├── github_utils.py              # Utility functions for GitHub integration
├── .env                         # Environment variables
```

## Prerequisites
* Python 3.8+
* [Ollama](https://ollama.com) with `granite3.3` pulled
* **PostgreSQL** with `pgvector` extension enabled
* A GitHub bot set up as follows:

  - With permissions to read and write repository contents and comments on pull requests and issues:
  
  ![image](https://github.com/user-attachments/assets/92f4472b-08e4-4cc2-9bca-002d49dbec93)


  ![image](https://github.com/user-attachments/assets/2149b3ad-792f-433c-9f41-7df6e330c3b0)

  
  ![image](https://github.com/user-attachments/assets/9357f981-02f7-4fda-99aa-e89a68b992b9)


   - Subscribed to events for comments created in issues and pull requests:

  ![image](https://github.com/user-attachments/assets/48f4a917-f287-4941-a770-05d58e68ec92)


  - Install the GitHub bot to the required repository.

## Setup Instructions
### 1. Install Dependencies
Make sure you have Python 3.8+ installed.
Install required Python packages:
```bash
pip install -r requirements.txt
```
Ensure you also have the following installed:
- **PostgreSQL** with `pgvector` extension enabled
- **Ollama** running locally with the `granite3.3` model pulled
To pull the model:
```bash
ollama pull granite3.3
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory with the following:
```env
DB_NAME=rag_db
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
GITHUB_BOT_SECRET=
GITHUB_BOT_ID=
REDIS_URL=
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
```
Update these values based on your PostgreSQL setup.

### 3. Start PostgreSQL with PgVector

Make sure your local PostgreSQL instance is running and has the `pgvector` extension installed:

To install postgres:
```
brew install postgresql
```

To install pgvector:
```
brew install pgvector
```

### ✅ To **create** your own database, use:

```bash
createdb -U <your_user> <db_name>
```


To connect to the database:
```
psql -U <your_user> -d <db_name>
```

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
## 🔍 Usage

### Start script

```bash
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
* 🔍 Vector DB: PostgreSQL + PgVector (local)
* 🧠 LLM: Granite Code (via Ollama)
* 📎 RAG: Context retrieved from `guide/*.txt`
* 🛠 Fixes: LLM rewrites chunks while preserving validation and descriptions

## 🛑 Notes

* Only the `variables.tf` file is currently reviewed.
* Descriptions and validation blocks are never altered.
* No extra explanations are included in the final fixed code.