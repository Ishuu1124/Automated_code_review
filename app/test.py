from app.db.indexer import index_docs
from dotenv import load_dotenv

load_dotenv()
DATA_DIR = "app/guide"

index_docs(DATA_DIR)