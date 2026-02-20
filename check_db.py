import os
import sqlite3
from datetime import datetime

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'psychelife.db')

def get_db_stats():
    if not os.path.exists(DB_PATH):
        return None
    
    stats = os.stat(DB_PATH)
    last_mod = datetime.fromtimestamp(stats.st_mtime)
    file_size = stats.st_size  # in bytes
    
    return {
        'time': last_mod,
        'size': file_size,
        'readable_time': last_mod.strftime('%Y-%m-%d %H:%M:%S'),
        'readable_size': f"{file_size / 1024:.2f} KB"
    }

def check_database():
    print(f"--- Database Change Monitor ---")
    stats = get_db_stats()

    if stats is None:
        print("❌ STATUS: File does not exist!")
        return

    print(f"📍 Last Changed: {stats['readable_time']}")
    print(f"📦 Current Size: {stats['readable_size']}")

    # Integrity Check: Count actual data to see if the content changed
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Checking patient and visit counts
        cursor.execute("SELECT COUNT(*) FROM patients")
        p_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM visits")
        v_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"👥 Patient Records: {p_count}")
        print(f"📅 Total Visits: {v_count}")
        
        # Logic to detect if it's a "fresh" vs "working" DB
        if p_count == 0 and stats['size'] < 20000: # Small size + 0 records
            print("⚠️  WARNING: Database looks like a fresh/empty initialization.")
        else:
            print("✅ STATUS: Database contains active data.")

    except sqlite3.Error as e:
        print(f"❌ ERROR: Database file is corrupted or unreadable: {e}")

if __name__ == "__main__":
    check_database()
