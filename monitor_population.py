import sqlite3
import time

DB_PATH = 'tennis_data.db'

def monitor():
    conn = sqlite3.connect(DB_PATH, timeout=10) # 10s timeout
    cursor = conn.cursor()
    
    print("Monitoring DB growth (matches table)...")
    for i in range(5):
        try:
            cursor.execute("SELECT count(*) FROM matches")
            count = cursor.fetchone()[0]
            print(f"[{time.strftime('%H:%M:%S')}] Matches: {count}")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(2)
        
    conn.close()

if __name__ == "__main__":
    monitor()
