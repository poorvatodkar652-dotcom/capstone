import sqlite3

def migrate():
    conn = None
    try:
        conn = sqlite3.connect('instance/hostel.db')
        cursor = conn.cursor()
        
        # Rename column
        cursor.execute("ALTER TABLE gatepass_requests RENAME COLUMN qr_file_path TO auth_code;")
        
        conn.commit()
        print("Successfully renamed qr_file_path to auth_code in gatepass_requests table.")
    except sqlite3.OperationalError as e:
        print(f"Migration error (might already be applied): {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate()
