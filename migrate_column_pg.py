import os
import psycopg2
from dotenv import load_dotenv

def migrate():
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Rename column
        cursor.execute("ALTER TABLE gatepass_requests RENAME COLUMN qr_file_path TO auth_code;")
        
        conn.commit()
        print("Successfully renamed qr_file_path to auth_code in gatepass_requests table.")
    except Exception as e:
        print(f"Migration error (might already be applied): {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate()
