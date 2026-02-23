
import csv
import io
import requests
import tennis_db

ATP_PLAYERS_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_players.csv"
WTA_PLAYERS_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_players.csv"

def import_profiles():
    conn = tennis_db.get_connection()
    c = conn.cursor()
    
    # Ensure table exists
    c.execute('''
    CREATE TABLE IF NOT EXISTS sackmann_profiles (
        sackmann_id TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        full_name TEXT,
        country TEXT,
        dob TEXT,
        tour TEXT
    )
    ''')
    
    def process_url(url, tour):
        print(f"Fetching {url}...")
        try:
            r = requests.get(url)
            r.raise_for_status()
            reader = csv.reader(r.text.splitlines())
            header = next(reader) # player_id,name_first,name_last,hand,dob,ioc,height,wikidata_id
            
            profiles = []
            for row in reader:
                if not row or len(row) < 6: continue
                
                try:
                    pid = row[0] # Keep as string
                    first = row[1].strip()
                    last = row[2].strip()
                    full = f"{first} {last}".strip()
                    dob = row[4].strip() if row[4] else None
                    country = row[5].strip() if row[5] else None
                    
                    prefixed_id = f"{tour}_{pid}"
                    
                    profiles.append((prefixed_id, first, last, full, country, dob, tour))
                    
                except ValueError:
                    continue
            
            c.executemany("""
                INSERT OR REPLACE INTO sackmann_profiles 
                (sackmann_id, first_name, last_name, full_name, country, dob, tour)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, profiles)
            conn.commit()
            print(f"  Imported {len(profiles)} profiles for {tour}")
            
        except Exception as e:
            print(f"Error processing {tour}: {e}")

    process_url(ATP_PLAYERS_URL, 'atp')
    process_url(WTA_PLAYERS_URL, 'wta')
    
    conn.close()

if __name__ == "__main__":
    import_profiles()
