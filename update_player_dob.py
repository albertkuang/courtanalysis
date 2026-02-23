import sqlite3
from datetime import datetime

def update_dobs():
    conn = sqlite3.connect('tennis_data.db')
    c = conn.cursor()
    
    print("Fetching Sackmann Profiles...")
    c.execute("SELECT full_name, dob FROM sackmann_profiles WHERE dob IS NOT NULL")
    profiles = c.fetchall()
    
    print(f"Found {len(profiles)} profiles with DOB.")
    
    updated = 0
    for name, dob_str in profiles:
        if not dob_str or len(dob_str) != 8:
            continue
            
        try:
            # Convert YYYYMMDD to YYYY-MM-DDT00:00:00
            dt = datetime.strptime(dob_str, '%Y%m%d')
            formatted_dob = dt.strftime('%Y-%m-%dT00:00:00')
            
            # Update players table if birth_date is NULL
            # Match by Name (Exact)
            c.execute("UPDATE players SET birth_date = ? WHERE name = ? AND birth_date IS NULL", (formatted_dob, name))
            if c.rowcount > 0:
                updated += c.rowcount
        except ValueError:
            continue
            
    conn.commit()
    print(f"Updated {updated} players with DOB.")
    conn.close()

if __name__ == "__main__":
    update_dobs()
