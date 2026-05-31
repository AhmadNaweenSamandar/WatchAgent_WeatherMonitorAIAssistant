import sqlite3
import json
import os

DB_PATH = os.getenv("DATABASE_URL", "data/weather.db")
# Clean up the path format if it contains the async prefix used in SQLAlchemy
if DB_PATH.startswith("sqlite+aiosqlite:///"):
    DB_PATH = DB_PATH.replace("sqlite+aiosqlite:///", "")

def analyze_event_frequency():
    """Extracts event frequencies for the Cursor Agent to analyze."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT event_type, COUNT(*) as trigger_count 
            FROM events 
            GROUP BY event_type
        """)
        
        results = [dict(row) for row in cursor.fetchall()]
        print(json.dumps({"status": "success", "data": results}, indent=2))
        
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    analyze_event_frequency()