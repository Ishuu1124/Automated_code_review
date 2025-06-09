from pymilvus import (
    connections,
    utility,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
)
import os

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
COLLECTION_NAME = "docs"


def connect_milvus():
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)


def init_milvus():
    connect_milvus()
    if not utility.has_collection(COLLECTION_NAME):
        fields = [
            FieldSchema(
                name="path", dtype=DataType.VARCHAR, max_length=512, is_primary=True
            ),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="content_hash", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
        ]
        schema = CollectionSchema(fields)
        Collection(name=COLLECTION_NAME, schema=schema)
