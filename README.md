# Terraform RAG Evaluation with Granite 3.2
- This project compares Terraform code files (`variables.tf`) against best practices using **Simple RAG (Retrieval-Augmented Generation)** powered by **Granite 3.2** LLM (via Ollama). The system retrieves reference context from ingested `.txt` and `.tf` documents, and evaluates target Terraform files for potential improvements.
- Arcihtecture Diagram:
![image](https://github.com/user-attachments/assets/29803658-8b0f-4a66-8354-561b4e6b0eff)

---
## Features
- **Granite 3.2** LLM integration via Ollama.
- Ingests Terraform best practices and examples from `.txt` and `.tf` files.
- Embeds documents using `sentence-transformers` and stores them in **pgVector (PostgreSQL)**.
- Retrieves top relevant context to construct prompts for code evaluation.
- Scores generated suggestions using:
  - Simple similarity score
  - Answer length
  - Keyword overlap
- CLI-based runner for testing any given `variables.tf` file.
---
## Setup Instructions
### 1. Install Dependencies
Make sure you have Python 3.8+ installed.
Install required Python packages:
```bash
pip install -r requirements.txt
```
Ensure you also have the following installed:
- **PostgreSQL** with `pgvector` extension enabled
- **Ollama** running locally with the `granite3.2` model pulled
To pull the model:
```bash
ollama pull granite3.2
```
---
### 2. Configure Environment Variables
Create a `.env` file in the root directory with the following:
```env
DB_NAME=rag_db
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```
Update these values based on your PostgreSQL setup.
---
### 3. Index Reference Documents
Run the following to index documents into the vector database:
```bash
python db/indexer.py
```
This step creates embeddings and stores them in PostgreSQL using `pgvector`.
---
### 4. Evaluate a Terraform File
Place the `variables.tf` file you want to analyze inside the `sample_tf/` directory.
Then run:
```bash
python app.py
```
This will:
- Retrieve relevant context from the database
- Generate improvement suggestions using Granite 3.2
- Print basic evaluation metrics (similarity score, response length)
---
