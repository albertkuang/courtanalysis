import sqlite3

def add_column():
    conn = sqlite3.connect('tennis_data.db')
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(players)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'last_college_check' not in columns:
        print("Adding 'last_college_check' column...")
        try:
            cursor.execute("ALTER TABLE players ADD COLUMN last_college_check DATETIME")
            conn.commit()
            print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("'last_college_check' column already exists.")

    conn.close()

if __name__ == "__main__":
    add_column()
