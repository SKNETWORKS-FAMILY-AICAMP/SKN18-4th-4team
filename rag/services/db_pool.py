import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import os

load_dotenv()

class DatabasePool:
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if DatabasePool._pool is None:
            DatabasePool._pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                host=os.getenv("PGHOST", "127.0.0.1"),
                port=os.getenv("PGPORT", "5432"),
                user=os.getenv("PGUSER", "root"),
                password=os.getenv("PGPASSWORD", "root1234"),
                database=os.getenv("PGDATABASE", "sknproject4")
            )
            print("✅ PostgreSQL 연결 풀 생성 완료")

    def get_connection(self):
        return DatabasePool._pool.getconn()

    def put_connection(self, conn):
        DatabasePool._pool.putconn(conn)

    def close_all(self):
        DatabasePool._pool.closeall()
