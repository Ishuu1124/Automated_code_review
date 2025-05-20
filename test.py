import time
import logging
from pymilvus import connections

logging.basicConfig(level=logging.DEBUG)

time.sleep(10)

connections.connect(host="127.0.0.1", port="19530")
print("✅ Successfully connected to Milvus!")

