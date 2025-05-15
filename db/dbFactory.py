import os
import psycopg
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from pymilvus import connections, utility, Collection, CollectionSchema, FieldSchema, DataType

load_dotenv()

class db(ABC):
    # def __init__(self):
        # pass
    
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def initialise(self):
        pass
    
    @abstractmethod
    def add_index(self):
        pass

class Postgres(db):
    def __init__(self):
        self.DB_NAME = os.getenv("DB_NAME")
        self.DB_USER = os.getenv("DB_USER")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD")
        self.DB_HOST = os.getenv("DB_HOST", "localhost")
        self.DB_PORT = os.getenv("DB_PORT", "5432")
        
    def connect(self):
        return psycopg.connect(
            dbname=self.DB_NAME,
            user=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT
        )
    
    def initialise(self):
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;
                CREATE TABLE IF NOT EXISTS docs (
                    id SERIAL PRIMARY KEY,
                    path TEXT,
                    chunk_index INT,
                    content TEXT,
                    content_hash TEXT,
                    embedding vector(384),
                    UNIQUE(path, chunk_index)
                );
            """)
            conn.commit()
        conn.close()
    
    def add_index(self, path, chunk_index, content, content_hash, embedding):
        try:
            conn = self.connect()
            with conn.cursor() as cur:
                cur.execute("SELECT content_hash FROM docs WHERE path = %s AND chunk_index = %s", (path, chunk_index))
                row = cur.fetchone()
                if not row or row[0] != content_hash:
                    cur.execute("""
                        INSERT INTO docs (path, chunk_index, content, content_hash, embedding)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (path, chunk_index) DO UPDATE SET
                            content = EXCLUDED.content,
                            content_hash = EXCLUDED.content_hash,
                            embedding = EXCLUDED.embedding;
                    """, (path, chunk_index, content, content_hash, embedding.tolist()))
                conn.commit()
            conn.close()
            return 0
        except Exception as e:
            print(f"[ERROR] Could not add index: {e}")
            return 1

class Milvus(db):
    def __init__(self):
        self.MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
        self.MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
        self.COLLECTION_NAME = "docs"
        
    def connect(self):
        connections.connect(host=self.MILVUS_HOST, port=self.MILVUS_PORT)
        return
    
    def initialise(self):
        self.connect()
        if not utility.has_collection(self.COLLECTION_NAME):
            fields = [
                FieldSchema(name="path", dtype=DataType.VARCHAR, max_length=512, is_primary=True),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="content_hash", dtype=DataType.VARCHAR, max_length=128),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
            ]
            schema = CollectionSchema(fields)
            Collection(name=self.COLLECTION_NAME, schema=schema)
    
    def add_index(self, path, chunk_index, content, content_hash, embedding):
        try:
            collection = Collection(self.COLLECTION_NAME)
            to_insert = {"path": [], "chunk_index": [], "content": [], "content_hash": [], "embedding": []}
            expr = f'path == "{path}" && chunk_index == {chunk_index}'
            collection.load()
            results = collection.query(expr, output_fields=["content_hash"])

            if not results or results[0]["content_hash"] != content_hash:
                to_insert["path"].append(path)
                to_insert["chunk_index"].append(chunk_index)
                to_insert["content"].append(content)
                to_insert["content_hash"].append(content_hash)
                to_insert["embedding"].append(embedding.tolist())

            if to_insert["path"]:
                collection.insert([to_insert["path"], to_insert["chunk_index"], to_insert["content"], to_insert["content_hash"], to_insert["embedding"]])
            return 0
        except Exception as e:
            print(f"[ERROR] Could not add index: {e}")
            return 1

class dbFactory:
    @staticmethod
    def makedb(service_name, *args):
        if service_name == "postgres":
            return Postgres(*args)
        elif service_name == "milvus":
            return Milvus(*args)