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
    
    # @abstractmethod
    # def initialise(self):
    #     pass
    
    @abstractmethod
    def add_index(self):
        pass
    
    @abstractmethod
    def get_top_k_chunks(self):
        pass
    
    @abstractmethod
    def close_conn(self)->int:
        pass

class Milvus(db):
    def __init__(self):
        self.MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
        self.MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
        self.COLLECTION_NAME = "docs"
        connections.connect(host=self.MILVUS_HOST, port=self.MILVUS_PORT)
        if not utility.has_collection(self.COLLECTION_NAME):
            fields = [
                FieldSchema(name="path", dtype=DataType.VARCHAR, max_length=512, is_primary=True),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="content_hash", dtype=DataType.VARCHAR, max_length=128),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
            ]
            schema = CollectionSchema(fields)
            self.collection = Collection(name=self.COLLECTION_NAME, schema=schema)
        else:
            self.collection = Collection(name=self.COLLECTION_NAME)
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "IP",
            "params": {"nlist": 128}
        }
        self.collection.create_index(field_name="embedding", index_params=index_params)
            
    def connect(self):
        connections.connect(alias='conn', host=self.MILVUS_HOST, port=self.MILVUS_PORT)
    
    def add_index(self, path, chunk_index, content, content_hash, embedding):
        try:
            to_insert = {"path": [], "chunk_index": [], "content": [], "content_hash": [], "embedding": []}
            expr = f'path == "{path}" && chunk_index == {chunk_index}'
            self.collection.load()
            results = self.collection.query(expr, output_fields=["content_hash"])

            if not results or results[0]["content_hash"] != content_hash:
                to_insert["path"].append(path)
                to_insert["chunk_index"].append(chunk_index)
                to_insert["content"].append(content)
                to_insert["content_hash"].append(content_hash)
                to_insert["embedding"].append(embedding.tolist())

            if to_insert["path"]:
                self.collection.insert([to_insert["path"], to_insert["chunk_index"], to_insert["content"], to_insert["content_hash"], to_insert["embedding"]])
            return 0
        except Exception as e:
            print(f"[ERROR] Could not add index: {e}")
            return 1
        
    def get_top_k_chunks(self, query_embedding, k=5):
        self.collection.load()
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        search_results = self.collection.search(
            data=[query_embedding.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=k,
            expr=None,
            output_fields=["path", "chunk_index", "content"]
        )
        return search_results[0]
        
    def close_conn(self):
        try:
            connections.disconnect(alias='conn')
            return 0
        except Exception as e:
            print(f"[ERROR] Could not close connection: {e}")
            return 1

class dbFactory:
    @staticmethod
    def makedb(service_name, *args):
        if service_name == "postgres":
            return Postgres(*args)
        elif service_name == "milvus":
            return Milvus(*args)