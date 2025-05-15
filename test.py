from pymilvus import connections
connections.connect()
connections.get_connection().is_connected 