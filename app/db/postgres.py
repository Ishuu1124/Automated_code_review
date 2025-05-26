from app.db.dbFactory import db
import yaml
import psycopg
import os

class Postgres(db):
    def __init__(self):
        self.DB_NAME:str = os.getenv("DB_NAME", "")
        self.DB_USER:str = os.getenv("DB_USER", "")
        self.DB_PASSWORD:str = os.getenv("DB_PASSWORD", "")
        self.DB_HOST:str = os.getenv("DB_HOST", "localhost")
        self.DB_PORT:str = os.getenv("DB_PORT", "5432")
        self.conn = psycopg.connect(
            dbname=self.DB_NAME,
            user=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT
        )
        with self.conn.cursor() as cur:
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
            self.conn.commit()
            
    def connect(self):
        return psycopg.connect(
            dbname=self.DB_NAME,
            user=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT
        )
    
    def add_index(self, path, chunk_index, content, content_hash, embedding):
        try:
            with self.conn.cursor() as cur:
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
                self.conn.commit()
            return 0
        except Exception as e:
            print(f"[ERROR] Could not add index: {e}")
            return 1
        
    def get_top_k_chunks(self, query_embedding, k=5, filter_by_filename="variables.tf"):
        with self.conn.cursor() as cur:
            sql = """
                SELECT path, chunk_index, content, content_hash, embedding
                FROM docs
            """
            if filter_by_filename:
                sql += f" WHERE path LIKE '%%{filter_by_filename}'"
            sql += " ORDER BY embedding <-> %s::vector LIMIT %s"
            cur.execute(sql, (query_embedding.tolist(), k))
            context_chunks = cur.fetchall()
        return context_chunks
    
    def close_conn(self):
        try:
            self.conn.close()
            return 0
        except Exception as e:
            print(f"[ERROR] Could not close connection: {e}")
            return 1