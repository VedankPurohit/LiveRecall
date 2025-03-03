import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

class DBConnection:
    def __init__(self, dbname="ImgVec ", user="postgres", password="root", host="localhost", port="5432"):
        self.connection_string = f"dbname={dbname} user={user} password={password} host={host} port={port}"
        self.conn = None
        self.cur = None
        
    def connect(self):
        try:
            self.conn = psycopg2.connect(self.connection_string)
            self.cur = self.conn.cursor()
            register_vector(self.conn)
            return True
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return False
            
    def disconnect(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
            
    def execute(self, query, params=None):
        try:
            if params:
                self.cur.execute(query, params)
            else:
                self.cur.execute(query)
            self.conn.commit()
            return True
        except Exception as e:
            # self.conn.rollback()
            print(f"Error executing query: {e}")
            return False
            
    def fetch_all(self):
        return self.cur.fetchall()
        
    def fetch_one(self):
        return self.cur.fetchone()
        
    def initialize_memory_tables(self):
        """Create the necessary tables if they don't exist"""
        try:
            # Create the memory table with pgvector extension
            # self.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create memory table
            self.execute("""
                CREATE TABLE IF NOT EXISTS LiveRecall (
                    id SERIAL PRIMARY KEY,
                    image_path TEXT NOT NULL,
                    embedding vector(768),
                    timestamp TEXT NOT NULL
                );
            """)
            
            # Create index for similarity search
            self.execute("""
                CREATE INDEX IF NOT EXISTS memory_embedding_idx 
                ON LiveRecall 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            
            return True
        except Exception as e:
            print(f"Error initializing tables: {e}")
            return False

# Create a global database connection instance
db = DBConnection()

if __name__ == "__main__":
    db.connect()
    db.initialize_memory_tables() 