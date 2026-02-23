
import sqlite3
import os

DB_MAIN = r'C:\work\github\courtanalysis\tennis_data.db'
DB_SOURCE = r'C:\work\github\courtanalysis\bck\tennis_data.db'

def sync_matches():
    if not os.path.exists(DB_SOURCE):
        print(f"Error: Source database not found at {DB_SOURCE}")
        return

    print(f"Connecting to {DB_MAIN}...")
    conn = sqlite3.connect(DB_MAIN)
    cursor = conn.cursor()

    try:
        # Attach the source database
        print(f"Attaching {DB_SOURCE}...")
        cursor.execute(f"ATTACH DATABASE '{DB_SOURCE}' AS source_db")

        # Check counts
        cursor.execute("SELECT count(*) FROM main.matches")
        main_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT count(*) FROM source_db.matches")
        source_count = cursor.fetchone()[0]

        print(f"Current matches in MAIN DB:   {main_count}")
        print(f"Matches in BACKUP/SOURCE DB: {source_count}")

        if source_count <= main_count:
            print("WARNING: Source has fewer or equal records. Proceeding anyway as requested...")
        
        # Verify columns match (simple check)
        cursor.execute("PRAGMA main.table_info(matches)")
        main_cols = {row[1] for row in cursor.fetchall()}
        
        cursor.execute("PRAGMA source_db.table_info(matches)")
        source_cols = {row[1] for row in cursor.fetchall()}

        if main_cols != source_cols:
            print(f"WARNING: Schema mismatch!\nMain: {main_cols}\nSource: {source_cols}")
            user_input = input("Schemas differ. Type 'yes' to try force overwrite, anything else to cancel: ")
            if user_input.lower() != 'yes':
                print("Operation cancelled.")
                return

        print("Starting transaction...")
        conn.execute("BEGIN TRANSACTION")

        print("Deleting old records from main.matches...")
        cursor.execute("DELETE FROM main.matches")

        print("Inserting records from source_db.matches...")
        # explicitly listing columns is safer but * assuming schema match for speed/simple script
        cursor.execute("INSERT INTO main.matches SELECT * FROM source_db.matches")

        conn.commit()
        print("Successfully synchronized matches table.")
        
        # Final count check
        cursor.execute("SELECT count(*) FROM main.matches")
        new_count = cursor.fetchone()[0]
        print(f"New match count in MAIN DB: {new_count}")

    except Exception as e:
        conn.rollback()
        print(f"An error occurred: {e}")
        print("Transaction rolled back.")
    finally:
        conn.close()

if __name__ == "__main__":
    sync_matches()
