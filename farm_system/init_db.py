import os
from database import get_connection

def init_db():
    """Ustvari tabele v bazi na podlagi schema.sql."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    conn = get_connection()
    try:
        conn.executescript(schema_sql)
        print("Database initialized")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
